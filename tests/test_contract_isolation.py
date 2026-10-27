"""Ізоляція legacy/enums, content accuracy та цілісність нових input."""

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import aggregate_runs
import evaluator
import generate_report
import main
from schema_contracts import CONTRACT_VERSION, CONTRACT_SHA256, LEGACY_CONTRACT_VERSION
from test_evaluator import golden_record, result_record


class ContractIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.golden = {"HR-1": golden_record()}

    def strict_record(self, document_id="HR-1"):
        record = result_record(document_id)
        path = self.root / f"{document_id}.txt"
        path.write_text("Title\nBody\n", encoding="utf-8")
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        record.update(contract_version=CONTRACT_VERSION, contract_sha256=CONTRACT_SHA256,
                      provider="openai", requested_model=record["model"], actual_model="snapshot",
                      source_path=str(path), source_sha256=checksum, input_sha256=checksum,
                      preparation_version=main.PREPARATION_VERSION)
        record["result"].update(first_attempt_valid=True, repair_attempted=False,
                                first_attempt_seconds=1.0, seconds=1.1,
                                input_tokens=100, output_tokens=50)
        if document_id in self.golden:
            self.golden[document_id]["source_sha256"] = checksum
        return record

    def write_run(self, name, records):
        path = self.root / name
        path.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
        return path

    def test_language_error_does_not_reduce_seven_field_content_accuracy(self):
        record = self.strict_record()
        record["result"]["data"]["language"] = "en"
        report = evaluator.evaluate_run([record], self.golden)
        self.assertEqual(report["aggregate_accuracy"], 7 / 8)
        self.assertEqual(report["content_accuracy"], 1)
        self.assertEqual(len(report["content_field_accuracy"]), 7)
        self.assertNotIn("language", report["content_field_accuracy"])

    def test_strict_unknown_case_and_duplicate_payloads_are_invalid_not_corrected(self):
        for values in (["Telegram"], ["Arduino"], ["arduino", "arduino"]):
            with self.subTest(values=values):
                record = self.strict_record()
                record["result"]["data"]["mentioned_platforms"] = values
                report = evaluator.evaluate_run([record], self.golden)
                self.assertEqual(report["document_status_counts"]["invalid"], 1)
                self.assertEqual(report["aggregate_accuracy"], 0)
                self.assertEqual(report["content_accuracy"], 0)

    def test_repaired_final_result_is_scored_and_missing_document_stays_zero(self):
        record = self.strict_record()
        record["result"].update(first_attempt_valid=False, repair_attempted=True)
        self.golden["HR-2"] = golden_record("HR-2")
        report = evaluator.evaluate_run([record], self.golden)
        self.assertEqual(report["aggregate_accuracy"], 0.5)
        self.assertEqual(report["content_accuracy"], 0.5)
        self.assertEqual(report["document_status_counts"]["missing"], 1)

    def test_unknown_missing_and_modified_contract_hashes_are_rejected(self):
        for field, value in (("contract_version", "unknown"), ("contract_sha256", "bad"),
                             ("provider", "unknown"), ("requested_model", "different")):
            record = self.strict_record()
            record[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                evaluator.evaluate_run([record], self.golden)
        record = self.strict_record()
        del record["contract_sha256"]
        with self.assertRaises(ValueError):
            evaluator.evaluate_run([record], self.golden)

    def test_mixed_contracts_rejected_within_and_between_files(self):
        strict = self.strict_record()
        legacy = result_record("HR-2")
        with self.assertRaises(ValueError):
            evaluator.evaluate_run([strict, legacy], self.golden)
        strict_path = self.write_run("new.jsonl", [strict])
        legacy_path = self.write_run("old.jsonl", [legacy])
        with self.assertRaises(ValueError):
            aggregate_runs.aggregate_files([strict_path, legacy_path])
        with self.assertRaises(ValueError):
            evaluator.select_run_files([strict_path, legacy_path])
        with self.assertRaises(ValueError):
            evaluator.select_run_files([legacy_path], CONTRACT_VERSION)

    def test_default_discovery_requires_selection_when_both_contracts_exist(self):
        self.write_run("old.jsonl", [result_record()])
        strict = self.strict_record()
        directory = self.root / CONTRACT_VERSION
        directory.mkdir()
        (directory / "new.jsonl").write_text(json.dumps(strict) + "\n", encoding="utf-8")
        with patch("evaluator.RESULTS", self.root):
            with self.assertRaises(ValueError):
                evaluator.select_run_files([])
            paths, version = evaluator.select_run_files([], CONTRACT_VERSION)
            self.assertEqual(version, CONTRACT_VERSION)
            self.assertEqual(len(paths), 1)
            paths, version = evaluator.select_run_files([], LEGACY_CONTRACT_VERSION)
            self.assertEqual(version, LEGACY_CONTRACT_VERSION)
            self.assertEqual(len(paths), 1)

    def test_source_path_and_actual_hashes_are_checked_for_new_results(self):
        for field, value in (("source_sha256", "bad"), ("input_sha256", "bad"),
                             ("source_path", str(self.root / "different.txt")),
                             ("preparation_version", "unknown")):
            record = self.strict_record()
            record[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                evaluator.evaluate_run([record], self.golden)

    def test_original_reports_reproduce_without_using_strict_validation(self):
        quality = json.loads((main.RESULTS / "evaluation/golden_20261026T095934403348Z.json").read_text(encoding="utf-8"))
        metrics = json.loads((main.RESULTS / "metrics/runs_20261026T101448227707Z.json").read_text(encoding="utf-8"))
        combined, _, _ = generate_report.match_reports(quality, metrics)
        self.assertEqual(len(combined), 8)
        self.assertEqual(sum(item["metrics"]["document_observations"] for item in combined), 240)

    def test_new_reports_join_only_with_the_same_contract(self):
        record = self.strict_record()
        path = self.write_run("new.jsonl", [record])
        golden_path = self.root / "golden.json"
        golden_path.write_text(json.dumps(list(self.golden.values())), encoding="utf-8")
        quality_run = evaluator.evaluate_run([record], self.golden)
        quality_run.update(source_path=str(path), source_sha256=generate_report.digest(path))
        header = {"contract_version": CONTRACT_VERSION, "contract_sha256": CONTRACT_SHA256}
        quality = dict(header, evaluator_version=evaluator.EVALUATOR_VERSION, provisional=False,
                       golden_path=str(golden_path), golden_sha256=generate_report.digest(golden_path), runs=[quality_run])
        metrics = dict(header, aggregator_version=aggregate_runs.AGGREGATOR_VERSION,
                       groups=aggregate_runs.aggregate_files([path]))
        combined, _, _ = generate_report.match_reports(quality, metrics)
        self.assertEqual(combined[0]["content_accuracy"], 1)
        legacy = dict(aggregator_version=aggregate_runs.LEGACY_AGGREGATOR_VERSION, groups=metrics["groups"])
        with self.assertRaises(ValueError):
            generate_report.match_reports(quality, legacy)


if __name__ == "__main__":
    unittest.main()
