"""Офлайн-перевірки ізоляції еталону та claim-level доказів LLM-судді."""

import json
import unittest
from pathlib import Path
from pydantic import ValidationError
from hardware_rag.answers import Answer
from hardware_rag.evaluation.judge import Judge
from rag_fixtures import FakeClient, chunk

# Промпти беруться з фактичного дерева проєкту без залежності від cwd.
ROOT = Path(__file__).resolve().parent.parent


class JudgeTests(unittest.TestCase):
    """Judge не може підтвердити факт джерелом іншого claim або пустою оцінкою.

    Тести перевіряють структурну чесність судді. Його реальна семантична
    точність усе одно потребує незалежного людського калібрування.
    """
    def test_per_claim_sources_cannot_be_replaced_by_another_claim(self):
        """Обидва IDs у контексті, але source c2 не є цитатою першого claim.

        Перевірка всього union IDs була б недостатньою й приховала б
        помилку підтримки кожного окремого фактичного твердження.
        """
        answer = Answer.model_validate_json(json.dumps({"status": "answered", "limitations": "",
                   "claims": [{"text": "First", "chunk_ids": ["c1"]}, {"text": "Second", "chunk_ids": ["c2"]}]}))
        response = {"claims": [{"text": "First", "claim_index": 0, "supported": True, "chunk_ids": ["c2"], "reason": "wrong source"},
                               {"text": "Second", "claim_index": 1, "supported": True, "chunk_ids": ["c2"], "reason": "ok"}]}
        client = FakeClient([json.dumps(response)])
        client.model = "synthetic-judge"
        judge = Judge(client, ROOT)
        with self.assertRaisesRegex(ValueError, "невалідні докази"):
            judge.faithful(answer, {"c1": chunk(), "c2": chunk("c2")})

    def test_faithfulness_has_no_reference_and_rejects_empty_claims(self):
        """Faithfulness отримує лише фактичний контекст, не еталон.

        Порожній claims output не може означати, що всі твердження
        підтверджені; це invalid judge response.
        """
        answer = Answer.model_validate_json('{"status":"answered","claims":[{"text":"3.3 V","chunk_ids":["c1"]}],"limitations":""}')
        client = FakeClient(['{"claims":[]}'])
        client.model = "synthetic-judge"
        judge = Judge(client, ROOT)
        with self.assertRaises(ValidationError):
            judge.faithful(answer, {"c1": chunk()})
        payload = json.loads(client.messages[0][-1]["content"])
        self.assertNotIn("reference", payload)
        self.assertEqual(payload["claims"][0]["sources"][0]["chunk_id"], "c1")

    def test_not_found_skips_semantic_faithfulness_call(self):
        """Чесна відмова без фактів має N/A faithfulness і не оплачує judge.

        Це не робить false-abstain на answerable питанні успішним:
        його окремо оцінює scoring-функція.
        """
        client = FakeClient([])
        client.model = "synthetic-judge"
        judge = Judge(client, ROOT)
        answer = Answer(status="not_found", claims=[], limitations="")
        self.assertEqual(judge.faithful(answer, {}), (None, []))
        self.assertEqual(client.attempts, [])
