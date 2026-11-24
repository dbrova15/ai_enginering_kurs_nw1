"""Знаменники eval, human-review gate й перевірка доказів без реальної LLM."""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from hardware_rag.answers import Answer, Result
from hardware_rag.eval_cases import EvalCase, Evidence
from hardware_rag.evaluation.dataset import lint
from hardware_rag.evaluation.draft import make_draft
from hardware_rag.evaluation.reporting import render_report
from hardware_rag.evaluation.scoring import aggregate, calibration, contains_fact, gate, retrieval_metrics, score
from rag_fixtures import chunk


def cases_fixture():
    """Створює 20 синтетичних кейсів усіх потрібних типів для lint tests.

    Approved стосується тільки явно test-only еталонів. Не змінює
    ручні статуси реального HardwareResearch testset.
    """
    cases = []
    text = chunk().text
    for i in range(20):
        answerable = i < 18
        tags = ["outdated_version"] if i < 2 else ["similar_model"] if i < 4 else []
        if not answerable:
            tags = ["no_answer"]
        cases.append(EvalCase(case_id=f"q{i}", question=f"Питання {i}?", language="uk", answerable=answerable,
                     reference="3.3 V" if answerable else "", relevant=["c1"] if answerable else [],
                     evidence=[Evidence(block_id="b1", start=0, end=len(text))] if answerable else [],
                     facts=[["3.3 V"]] if answerable else [], scoring_mode="deterministic",
                     retrieval_member=i < 15, tags=tags, review_status="approved"))
    return cases


class EvaluationTests(unittest.TestCase):
    """Перевіряє, що неповні чи непідтверджені дані не дають зелену якість.

    Метрики на fixtures мають відомі аналітичні значення й не входять
    у реальний REPORT ДЗ2.
    """
    def test_composite_draft_question_requires_both_evidence_fragments(self):
        """Питання про два підходи зберігає обидва докази, а не перший збіг.

        Reference, relevant та evidence мають охоплювати два різні блоки.
        Якщо один доказ відсутній, генератор відхиляє неповний еталон і
        не записує файл; жоден fixture не затверджує реальні human labels.
        """
        first, second = "Zerynth Studio method.", "MicroPython method."
        chunks = [chunk("z", first), chunk("m", second, spans=[("b2", 0, len(second))])]
        blocks = [{"block_id": "b1", "text": first, "kind": "paragraph", "ordinal": 0},
                  {"block_id": "b2", "text": second, "kind": "paragraph", "ordinal": 1}]
        questions = [("test", "Які два підходи?", (r"Zerynth Studio", r"MicroPython"), "uk", [])]
        with tempfile.TemporaryDirectory() as tmp, patch("hardware_rag.evaluation.draft.DRAFT_QUESTIONS", questions):
            path = Path(tmp)
            data = make_draft({"dataset_id": "fixture"}, chunks, blocks, path / "draft.json")
            case = data["cases"][0]
            self.assertEqual(case["reference"], first + "\n\n" + second)
            self.assertEqual(case["relevant"], ["m", "z"])
            self.assertEqual([item["block_id"] for item in case["evidence"]], ["b1", "b2"])
            self.assertEqual(case["review_status"], "draft")
            with self.assertRaises(ValueError):
                make_draft({"dataset_id": "fixture"}, chunks[:1], blocks, path / "missing.json")
            self.assertFalse((path / "missing.json").exists())

    def test_recall_and_mrr_have_different_meaning(self):
        """Два gold chunks дають recall 1/2, але перший правильний rank=2.

        Невдалий другий кейс залишається у знаменнику обох метрик.
        """
        metrics = retrieval_metrics([["wrong", "a"], []], [["a", "b"], ["c"]])
        self.assertEqual(metrics["recall_at_5"], 0.25)
        self.assertEqual(metrics["mrr_at_5"], 0.25)
        with self.assertRaises(ValueError):
            retrieval_metrics([["a", "a"]], [["a"]])

    def test_fact_boundaries_do_not_turn_30_into_3(self):
        """Literal matching зберігає одиниці й межі чисел та кодів.

        Типографський мінус і зайві пробіли не змінюють значення факту.
        """
        self.assertFalse(contains_fact("30 V", "3"))
        self.assertFalse(contains_fact("3.3 V", "3"))
        self.assertFalse(contains_fact("ESP32-S3", "ESP32"))
        self.assertTrue(contains_fact("3.3 V.", "3.3 V"))
        self.assertTrue(contains_fact("−15   °C", "-15 °c"))

    def test_failed_case_and_false_abstain_remain_in_denominator(self):
        """Відмова на answerable та технічна невдача не вилучаються з N.

        No-answer оцінюється окремо; невідома faithful не підвищує mean.
        """
        cases = cases_fixture()
        answerable, no_answer = cases[0], cases[-1]
        found = Answer.model_validate_json('{"status":"answered","claims":[{"text":"3.3 V","chunk_ids":["c1"]}],"limitations":""}')
        success = Result(status="success", answer=found, selected_ids=["c1"])
        failed = Result(status="failed", answer=None, selected_ids=[])
        refused = Result(status="success", answer=Answer(status="not_found", claims=[], limitations=""), selected_ids=[])
        scores = [score(success, answerable, faithful=True), score(failed, answerable), score(refused, no_answer)]
        metrics = aggregate(scores, [answerable, answerable, no_answer])
        self.assertEqual(metrics["correct"], 0.5)
        self.assertEqual(metrics["faithful"], 0.5)
        self.assertEqual(metrics["abstain"], 1.0)
        self.assertEqual(metrics["correct_count"], 2)

    def test_unknown_judge_is_incomplete_and_review_cannot_be_bypassed(self):
        """Недоступний judge або відсутня ручна перевірка провалюють gate.

        Навіть високі інші показники не компенсують ці prerequisites.
        """
        failures = gate({"correct": None, "complete": False}, {"correct": 0.8}, reviewed=False, calibrated=False)
        self.assertIn("testset_unreviewed", failures)
        self.assertIn("judge_uncalibrated", failures)
        self.assertIn("eval_incomplete", failures)
        self.assertIn("threshold:correct", failures)
        self.assertIn("threshold:correct", gate({"correct": float("nan"), "complete": True},
                                               {"correct": 0.8}, reviewed=True, calibrated=True))

    def test_calibration_requires_both_manual_classes(self):
        """Суддя, який завжди каже True, не калібрується лише на позитивних.

        FP/FN рахуються від усіх десяти ручних відповідей.
        """
        with self.assertRaises(ValueError):
            calibration([True] * 10, [True] * 10)
        metrics = calibration([True] * 10, [True] * 5 + [False] * 5)
        self.assertEqual(metrics["agreement"], 0.5)
        self.assertEqual(metrics["false_pass"], 0.5)

    def test_retrieval_report_does_not_claim_answer_validation(self):
        """Retrieval-only звіт показує відсутність генерацій і причини gate.

        Невідомі answer-метрики не стають нульовою чи успішною оцінкою;
        не створюється оманлива валідність 0/0 або рядок USD None.
        """
        report = render_report({"run_id": "offline", "provisional": True,
                                "metrics": {"agreement": None}, "records": [],
                                "gate_failures": ["judge_uncalibrated"], "cost_usd": None})
        self.assertIn("не вимірювали", report)
        self.assertIn("judge_uncalibrated", report)
        self.assertNotIn("0/0", report)
        self.assertNotIn("USD цього запуску: None", report)

    def test_lint_validates_proofs_coverage_and_manual_status(self):
        """Correct fixtures проходять, draft і stale proof IDs — ні.

        Це доводить поведінку lint, а не людську перевірку реального corpus.
        """
        cases = cases_fixture()
        envelope = {"dataset_id": "dataset", "review_status": "approved"}
        manifest = {"dataset_id": "dataset"}
        blocks = [{"block_id": "b1", "text": chunk().text}]
        self.assertEqual(lint(envelope, cases, manifest, [chunk()], blocks), [])
        cases[0] = cases[0].model_copy(update={"review_status": "draft", "relevant": ["unknown"]})
        problems = lint(envelope, cases, manifest, [chunk()], blocks)
        self.assertTrue(any("unknown" in p for p in problems))
        self.assertTrue(any("людина" in p for p in problems))
