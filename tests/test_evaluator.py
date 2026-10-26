"""Правила golden-оцінювання: знаменники, списки та цілісність прогонів."""

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import evaluator

EXPECTED = {
    "language": "uk", "primary_topic": "sensors_measurements",
    "mentioned_platforms": ["arduino"], "mentioned_interfaces": ["wifi", "bluetooth"],
    "mentions_sensor": True, "mentions_display": False,
    "mentions_battery": False, "mentions_motor": False,
}


def golden_record(document_id="HR-1"):
    return {"document_id": document_id, "schema_version": "v2",
            "annotation_status": "approved", "source_sha256": "a" * 64,
            "expected": copy.deepcopy(EXPECTED)}


def result_record(document_id="HR-1"):
    return {
        "document_id": document_id, "schema_version": "v2", "model": "test-model",
        "prompt_version": "v1", "prompt_sha256": "b" * 64,
        "sampling": {"temperature": 0, "top_p": 1}, "preparation_version": "test-v1",
        "source_sha256": "a" * 64, "input_sha256": "c" * 64,
        "result": {"ok": True, "status": "success", "data": copy.deepcopy(EXPECTED)},
    }


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.golden = {"HR-1": golden_record()}

    def evaluate(self, record):
        return evaluator.evaluate_run([record], self.golden)

    def test_perfect_prediction_and_list_order(self):
        record = result_record()
        record["result"]["data"]["mentioned_interfaces"].reverse()
        report = self.evaluate(record)
        self.assertEqual(report["aggregate_accuracy"], 1)
        self.assertTrue(all(value == 1 for value in report["field_accuracy"].values()))
        self.assertEqual(report["list_metrics"]["mentioned_interfaces"]["f1"], 1)

    def test_list_errors_are_binary_for_accuracy_and_partial_for_prf(self):
        record = result_record()
        record["result"]["data"]["mentioned_interfaces"] = ["wifi", "usb"]
        report = self.evaluate(record)
        self.assertEqual(report["field_accuracy"]["mentioned_interfaces"], 0)
        self.assertEqual(report["aggregate_accuracy"], 7 / 8)
        self.assertEqual(report["list_metrics"]["mentioned_interfaces"], {
            "tp": 1, "fp": 1, "fn": 1, "precision": 0.5, "recall": 0.5, "f1": 0.5,
        })

    def test_no_alias_case_or_whitespace_normalization(self):
        for value in ("Wi-Fi", "WIFI", " wifi "):
            with self.subTest(value=value):
                record = result_record()
                record["result"]["data"]["mentioned_interfaces"] = [value, "bluetooth"]
                self.assertEqual(self.evaluate(record)["field_accuracy"]["mentioned_interfaces"], 0)

    def test_duplicates_are_reported_but_do_not_change_set_score(self):
        record = result_record()
        record["result"]["data"]["mentioned_platforms"] = ["arduino", "arduino"]
        report = self.evaluate(record)
        self.assertEqual(report["aggregate_accuracy"], 1)
        self.assertEqual(report["documents"][0]["duplicate_list_values"], {"mentioned_platforms": ["arduino"]})

    def test_missing_document_stays_in_denominator(self):
        self.golden["HR-2"] = golden_record("HR-2")
        report = self.evaluate(result_record())
        self.assertEqual(report["aggregate_accuracy"], 0.5)
        self.assertEqual(report["document_status_counts"]["missing"], 1)
        self.assertEqual(report["list_metrics"]["mentioned_interfaces"]["recall"], 0.5)

    def test_list_prf_pools_counts_across_documents(self):
        self.golden["HR-2"] = golden_record("HR-2")
        self.golden["HR-2"]["expected"]["mentioned_interfaces"] = []
        first, second = result_record(), result_record("HR-2")
        first["result"]["data"]["mentioned_interfaces"] = ["wifi"]
        second["result"]["data"]["mentioned_interfaces"] = ["usb", "spi", "uart"]
        metrics = evaluator.evaluate_run([first, second], self.golden)["list_metrics"]["mentioned_interfaces"]
        self.assertEqual((metrics["tp"], metrics["fp"], metrics["fn"]), (1, 3, 1))
        self.assertEqual(metrics["precision"], 0.25)
        self.assertEqual(metrics["recall"], 0.5)
        self.assertAlmostEqual(metrics["f1"], 1 / 3)

    def test_failed_and_invalid_payloads_score_zero_for_every_field(self):
        cases = []
        failed = result_record()
        failed["result"] = {"ok": False, "status": "failed", "data": EXPECTED}
        cases.append(failed)
        for payload in (None, {}, dict(EXPECTED, mentions_sensor="true"),
                        dict(EXPECTED, language=None), dict(EXPECTED, extra="value")):
            record = result_record()
            record["result"]["data"] = payload
            cases.append(record)
        for record in cases:
            with self.subTest(record=record):
                report = self.evaluate(record)
                self.assertEqual(report["aggregate_accuracy"], 0)
                self.assertTrue(all(value == 0 for value in report["field_accuracy"].values()))

    def test_all_empty_sets_have_exact_match_and_undefined_prf(self):
        record = result_record()
        for field in evaluator.LIST_FIELDS:
            self.golden["HR-1"]["expected"][field] = []
            record["result"]["data"][field] = []
        report = self.evaluate(record)
        self.assertEqual(report["aggregate_accuracy"], 1)
        self.assertEqual(report["list_metrics"]["mentioned_interfaces"], {
            "tp": 0, "fp": 0, "fn": 0, "precision": None, "recall": None, "f1": None,
        })
        record["result"]["ok"] = False
        self.assertEqual(self.evaluate(record)["aggregate_accuracy"], 0)

    def test_non_golden_records_are_ignored_and_duplicate_ids_rejected(self):
        records = [result_record(), result_record("outside-golden")]
        report = evaluator.evaluate_run(records, self.golden)
        self.assertEqual(report["aggregate_accuracy"], 1)
        self.assertEqual(report["ignored_non_golden_results"], 1)
        with self.assertRaisesRegex(ValueError, "HR-1"):
            evaluator.evaluate_run([result_record(), result_record()], self.golden)

    def test_mixed_configurations_and_old_schema_are_rejected(self):
        for field, value in (("model", "other"), ("prompt_version", "v2"),
                             ("sampling", {"temperature": 0.7}), ("prompt_sha256", "d" * 64),
                             ("preparation_version", "other")):
            with self.subTest(field=field):
                other = result_record("HR-2")
                other[field] = value
                with self.assertRaises(ValueError):
                    evaluator.evaluate_run([result_record(), other], self.golden)
        record = result_record()
        record["schema_version"] = "v1"
        with self.assertRaises(ValueError):
            self.evaluate(record)

    def test_source_and_input_hash_conflicts_are_rejected(self):
        record = result_record()
        record["source_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "source_sha256"):
            self.evaluate(record)
        first = self.evaluate(result_record())
        record = result_record()
        record["input_sha256"] = "d" * 64
        second = self.evaluate(record)
        with self.assertRaisesRegex(ValueError, "input_sha256"):
            evaluator.verify_same_inputs([first, second])


class EvaluatorFileTests(unittest.TestCase):
    def test_cli_report_is_offline_provisional_and_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            golden = golden_record()
            golden["annotation_status"] = "needs_human_review"
            golden_path, run_path, output = root / "golden.json", root / "run.jsonl", root / "metrics.json"
            golden_path.write_text(json.dumps([golden]), encoding="utf-8")
            run_path.write_text(json.dumps(result_record()) + "\n", encoding="utf-8")
            args = [str(run_path), "--golden", str(golden_path), "--output", str(output)]
            with patch("main.OpenAI", side_effect=AssertionError("Мережа заборонена")), redirect_stdout(io.StringIO()):
                evaluator.main(args)
                report = json.loads(output.read_text(encoding="utf-8"))
                self.assertTrue(report["provisional"])
                self.assertEqual(report["runs"][0]["aggregate_accuracy"], 1)
                before = output.read_bytes()
                with self.assertRaises(FileExistsError):
                    evaluator.main(args)
                self.assertEqual(before, output.read_bytes())

    def test_invalid_golden_and_malformed_jsonl_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "data.json"
            for rows in ([], [golden_record(), golden_record()]):
                path.write_text(json.dumps(rows), encoding="utf-8")
                with self.assertRaises(ValueError):
                    evaluator.load_golden(path)
            record = golden_record()
            record["expected"]["mentioned_platforms"] *= 2
            path.write_text(json.dumps([record]), encoding="utf-8")
            with self.assertRaises(ValueError):
                evaluator.load_golden(path)
            path.write_text('{"document_id":', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, ":1"):
                evaluator.load_run(path)


if __name__ == "__main__":
    unittest.main()
