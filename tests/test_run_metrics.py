"""Перевірки знаменників, перцентилів, неповного usage й групування прогонів."""

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import aggregate_runs
import run_metrics
from test_evaluator import result_record


def metric_record(document_id="HR-1"):
    record = result_record(document_id)
    record["model"] = "gpt-4o-mini"
    record["result"].update(first_attempt_valid=True, repair_attempted=False,
                            first_attempt_seconds=1.0, seconds=1.1,
                            input_tokens=100, output_tokens=50)
    return record


class CalculationTests(unittest.TestCase):
    def test_validity_before_after_and_failed_latency(self):
        records = [metric_record(str(index))["result"] for index in range(3)]
        records[1].update(first_attempt_valid=False, repair_attempted=True, seconds=3)
        records[2].update(first_attempt_valid=False, repair_attempted=True,
                          ok=False, status="failed", data=None, seconds=100)
        metrics = run_metrics.summarize_results(records, "gpt-4o-mini")
        validity = metrics["validity"]
        self.assertEqual(validity["first_attempt_valid_rate"], 1 / 3)
        self.assertEqual(validity["final_valid_rate"], 2 / 3)
        self.assertEqual(validity["repair_attempted_rate"], 2 / 3)
        self.assertEqual(validity["repair_success_rate"], 0.5)
        self.assertEqual(metrics["latency"]["pipeline"]["p50_seconds"], 3)
        self.assertEqual(metrics["latency"]["pipeline"]["p95_seconds"], 100)

    def test_nearest_rank_for_30_documents(self):
        values = [{"seconds": number} for number in range(1, 31)]
        summary = run_metrics.latency_summary(values, "seconds")
        self.assertEqual((summary["p50_seconds"], summary["p95_seconds"]), (15, 29))
        self.assertTrue(summary["complete"])

    def test_missing_latency_is_visible_and_not_zero(self):
        summary = run_metrics.latency_summary([{"seconds": 4}, {"seconds": None}], "seconds")
        self.assertEqual(summary["samples"], 1)
        self.assertEqual(summary["missing"], 1)
        self.assertEqual(summary["p50_seconds"], 4)
        self.assertFalse(summary["complete"])
        empty = run_metrics.latency_summary([{}], "seconds")
        self.assertIsNone(empty["p95_seconds"])

    def test_cost_and_usage_per_1000_include_all_observations(self):
        result = metric_record()["result"]
        metrics = run_metrics.summarize_results([result, copy.deepcopy(result)], "gpt-4o-mini")
        self.assertEqual(metrics["usage"]["input_tokens"]["total"], 200)
        self.assertAlmostEqual(metrics["cost"]["estimated_api_usd"], 0.00009)
        self.assertAlmostEqual(metrics["cost"]["estimated_api_usd_per_1000_documents"], 0.045)

    def test_incomplete_usage_does_not_produce_complete_cost(self):
        first, second = metric_record()["result"], metric_record()["result"]
        second["output_tokens"] = None
        metrics = run_metrics.summarize_results([first, second], "gpt-4o-mini")
        self.assertIsNone(metrics["usage"]["output_tokens"]["total"])
        self.assertEqual(metrics["usage"]["output_tokens"]["known_total"], 50)
        self.assertFalse(metrics["cost"]["complete"])
        self.assertIsNone(metrics["cost"]["estimated_api_usd_per_1000_documents"])
        self.assertAlmostEqual(metrics["cost"]["known_usage_api_usd"], 0.00006)

    def test_local_zero_and_unknown_model_are_distinct(self):
        result = metric_record()["result"]
        result["input_tokens"] = result["output_tokens"] = None
        local = run_metrics.summarize_results([result], "llama3.2:3b")["cost"]
        unknown = run_metrics.summarize_results([result], "other-model")["cost"]
        self.assertTrue(local["complete"])
        self.assertEqual(local["estimated_api_usd_per_1000_documents"], 0)
        self.assertFalse(unknown["complete"])
        self.assertIsNone(unknown["estimated_api_usd"])

    def test_bad_numbers_and_inconsistent_flags_are_rejected(self):
        for field, value in (("seconds", -1), ("seconds", float("nan")),
                             ("seconds", float("inf")), ("input_tokens", True),
                             ("input_tokens", 1.5), ("output_tokens", -1),
                             ("first_attempt_valid", None), ("repair_attempted", True),
                             ("data", {})):
            with self.subTest(field=field, value=value):
                result = metric_record()["result"]
                result[field] = value
                with self.assertRaises(ValueError):
                    run_metrics.summarize_results([result], "gpt-4o-mini")


class AggregationFileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write_run(self, name, records):
        path = self.root / name
        path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
        return path

    def test_groups_separate_sampling_and_count_repeated_observations(self):
        first = self.write_run("first.jsonl", [metric_record()])
        repeated_record = metric_record()
        repeated_record["sampling"] = {"temperature": 0.0, "top_p": 1.0}
        repeated = self.write_run("repeat.jsonl", [repeated_record])
        other_record = metric_record()
        other_record["sampling"]["temperature"] = 0.7
        other = self.write_run("other.jsonl", [other_record])
        groups = aggregate_runs.aggregate_files([first, repeated, other])
        self.assertEqual(len(groups), 2)
        baseline = next(group for group in groups if group["run_count"] == 2)
        self.assertEqual(baseline["document_observations"], 2)
        self.assertEqual(baseline["unique_documents"], 1)

    def test_duplicates_and_conflicting_inputs_are_rejected(self):
        first = self.write_run("first.jsonl", [metric_record()])
        with self.assertRaises(ValueError):
            aggregate_runs.aggregate_files([first, first])
        duplicate = self.write_run("duplicate.jsonl", [metric_record(), metric_record()])
        with self.assertRaises(ValueError):
            aggregate_runs.aggregate_files([duplicate])
        changed = metric_record()
        changed["input_sha256"] = "d" * 64
        other = self.write_run("other.jsonl", [changed])
        with self.assertRaises(ValueError):
            aggregate_runs.aggregate_files([first, other])

    def test_json_and_markdown_are_offline_and_not_overwritten(self):
        path = self.write_run("run.jsonl", [metric_record()])
        output = self.root / "metrics.json"
        with patch("main.OpenAI", side_effect=AssertionError("Мережа заборонена")), redirect_stdout(io.StringIO()):
            aggregate_runs.main([str(path), "--output", str(output)])
            report = json.loads(output.read_text(encoding="utf-8"))
            markdown = output.with_suffix(".md").read_text(encoding="utf-8")
            self.assertEqual(len(report["groups"]), 1)
            self.assertIn("gpt-4o-mini", markdown)
            self.assertIn("0.045000", markdown)
            before = output.read_bytes()
            with self.assertRaises(FileExistsError):
                aggregate_runs.main([str(path), "--output", str(output)])
            self.assertEqual(output.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
