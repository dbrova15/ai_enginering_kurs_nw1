"""Зіставлення звітів, захист від застарілих даних і чесна генерація чернетки."""

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import aggregate_runs
import evaluator
import generate_report
import report_rendering
from test_evaluator import golden_record
from test_run_metrics import metric_record


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.golden_path, self.run = self.root / "golden.json", self.root / "run.jsonl"
        self.output = self.root / "REPORT.draft.md"
        goldens, self.records = [], []
        changes = [("primary_topic", "controllers_programming"), ("mentioned_interfaces", ["wifi"]),
                   ("mentioned_platforms", ["esp32"]), ("mentions_sensor", False), ("language", "en")]
        for number, (field, value) in enumerate(changes):
            document_id = f"HR-{number}"
            text = self.root / f"article {number}.txt"
            text.write_text(f"Article {number}", encoding="utf-8")
            golden, record = golden_record(document_id), metric_record(document_id)
            golden["source_sha256"] = record["source_sha256"] = generate_report.digest(text)
            record["source_path"] = str(text)
            record["result"]["data"][field] = value
            goldens.append(golden)
            self.records.append(record)
        self.golden_path.write_text(json.dumps(goldens), encoding="utf-8")
        self.write_run(self.run, self.records)
        self.refresh_reports()

    def write_run(self, path, records):
        path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")

    def refresh_reports(self, sources=None):
        self.golden = evaluator.load_golden(self.golden_path)
        sources = sources or [self.run]
        runs = []
        for source in sources:
            run = evaluator.evaluate_run(evaluator.load_run(source), self.golden)
            run.update(source_path=str(source.resolve()), source_sha256=generate_report.digest(source))
            runs.append(run)
        self.evaluation = {
            "evaluator_version": evaluator.EVALUATOR_VERSION,
            "golden_path": str(self.golden_path), "golden_sha256": generate_report.digest(self.golden_path),
            "provisional": any(row["annotation_status"] != "approved" for row in self.golden.values()),
            "runs": runs,
        }
        self.metrics = {"aggregator_version": aggregate_runs.AGGREGATOR_VERSION,
                        "assumptions": aggregate_runs.ASSUMPTIONS,
                        "groups": aggregate_runs.aggregate_files(sources)}

    def generate(self):
        evaluation_path, metrics_path = self.root / "evaluation.json", self.root / "metrics.json"
        evaluation_path.write_text(json.dumps(self.evaluation), encoding="utf-8")
        metrics_path.write_text(json.dumps(self.metrics), encoding="utf-8")
        with redirect_stdout(io.StringIO()), patch("main.OpenAI", side_effect=AssertionError("Мережа заборонена")):
            generate_report.main(["--evaluation", str(evaluation_path), "--metrics", str(metrics_path),
                                  "--output", str(self.output)])
        return self.output.read_text(encoding="utf-8")

    def test_draft_contains_all_tables_and_five_different_examples(self):
        text = self.generate()
        self.assertIn("ЧЕРНЕТКА", text)
        self.assertIn("87.50%", text)
        self.assertEqual(text.count("**Причина:** [ЗАПОВНЮЄ АВТОР"), 5)
        for field in evaluator.FIELDS:
            self.assertIn(field, text)
        self.assertIn("micro precision", text)
        self.assertIn("Вибір автора для production", text)
        self.assertIn("[ЗАПОВНЮЄ АВТОР одним абзацом", text)
        self.assertIn("article%20", text)
        self.assertFalse((self.root / "REPORT.md").exists())

    def test_sources_and_configurations_must_match(self):
        self.metrics["groups"][0]["configuration"]["prompt_version"] = "v2"
        with self.assertRaises(ValueError):
            generate_report.match_reports(self.evaluation, self.metrics)

    def test_tampered_metrics_are_rejected(self):
        self.metrics["groups"][0]["latency"]["pipeline"]["p95_seconds"] = 999
        with self.assertRaises(ValueError):
            generate_report.match_reports(self.evaluation, self.metrics)
        self.refresh_reports()
        self.evaluation["runs"][0]["aggregate_accuracy"] = 1
        with self.assertRaises(ValueError):
            generate_report.match_reports(self.evaluation, self.metrics)

    def test_changed_jsonl_or_golden_is_rejected(self):
        original = self.run.read_bytes()
        self.run.write_bytes(original + b"\n")
        with self.assertRaises(ValueError):
            generate_report.match_reports(self.evaluation, self.metrics)
        self.run.write_bytes(original)
        self.golden_path.write_bytes(self.golden_path.read_bytes() + b"\n")
        with self.assertRaises(ValueError):
            generate_report.match_reports(self.evaluation, self.metrics)

    def test_different_source_coverage_is_rejected(self):
        other = self.root / "other.jsonl"
        self.write_run(other, self.records)
        self.refresh_reports([self.run, other])
        self.evaluation["runs"].pop()
        with self.assertRaisesRegex(ValueError, "різні JSONL"):
            generate_report.match_reports(self.evaluation, self.metrics)

    def test_repeated_runs_combine_all_golden_observations(self):
        perfect = copy.deepcopy(self.records)
        for record in perfect:
            record["result"]["data"] = copy.deepcopy(self.golden[record["document_id"]]["expected"])
        other = self.root / "perfect.jsonl"
        self.write_run(other, perfect)
        self.refresh_reports([self.run, other])
        combined, _, _ = generate_report.match_reports(self.evaluation, self.metrics)
        self.assertEqual(len(combined), 1)
        self.assertEqual(combined[0]["golden_observations"], 10)
        self.assertEqual(combined[0]["aggregate_accuracy"], 75 / 80)

    def test_provisional_status_and_zero_errors_are_not_hidden(self):
        goldens = json.loads(self.golden_path.read_text(encoding="utf-8"))
        goldens[0]["annotation_status"] = "needs_human_review"
        self.golden_path.write_text(json.dumps(goldens), encoding="utf-8")
        for record in self.records:
            record["result"]["data"] = copy.deepcopy(self.golden[record["document_id"]]["expected"])
        self.write_run(self.run, self.records)
        self.refresh_reports()
        text = self.generate()
        self.assertIn("Попередні оцінки", text)
        self.assertIn("Знайдено лише 0", text)
        self.assertEqual(text.count("**Причина:**"), 0)

    def test_existing_report_is_not_overwritten(self):
        self.output.write_text("author text", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.generate()
        self.assertEqual(self.output.read_text(encoding="utf-8"), "author text")

    def test_markdown_cells_escape_untrusted_text_and_unknown_values(self):
        self.assertEqual(report_rendering.cell(None), "н/д")
        escaped = report_rendering.cell('<script>|`bad`\nnext')
        self.assertNotIn("<script>", escaped)
        self.assertNotIn("`", escaped)
        self.assertIn("\\|", escaped)


if __name__ == "__main__":
    unittest.main()
