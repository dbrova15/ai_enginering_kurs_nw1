"""LLM-суддя: окремі correctness і faithfulness без передавання еталону боту."""

from pathlib import Path
from pydantic import Field
from ..artifacts import canonical_json, digest
from ..documents import StrictRecord


class Verdict(StrictRecord):
    """Змістовний вердикт correctness із поясненням до рішення.

    reason потрібний для людського розбору розбіжностей; correct не
    вважається надійним до калібрування цього model/prompt fingerprint.
    """
    reason: str
    correct: bool


class SupportedClaim(StrictRecord):
    """Атомарний факт, його підтримка та конкретні процитовані докази.

    supported=True без source IDs не допускає faithful результату.
    Суддя не може вводити нові chunk IDs поза фактичним контекстом.
    """
    text: str
    claim_index: int = Field(ge=0)
    supported: bool
    chunk_ids: list[str]
    reason: str


class Faithfulness(StrictRecord):
    """Повний перелік атомарних фактів відповіді для semantic audit.

    Порожній список для змістовної відповіді є incomplete, не 100%
    підтримки. Усі фактичні речення мають бути перевірені, не лише цитати.
    """
    claims: list[SupportedClaim] = Field(min_length=1)


def structured_format(model, name: str) -> dict:
    """Створює strict response_format для конкретного judge-контракту.

    Одна функція застосовується до correctness і faithfulness, щоб
    технічні відмінності JSON parsing не впливали на семантичні оцінки.
    """
    return {"type": "json_schema", "json_schema": {"name": name, "strict": True,
                                                       "schema": model.model_json_schema()}}


class Judge:
    """Версійований judge із розділеними inputs correctness/faithfulness.

    Використовує спільний Budget generator/judge, але окрему модель
    й prompts. Не призначає власним калібрувальним labels статус approved.
    """
    def __init__(self, client, root: Path):
        """Читає два prompt-файли та обчислює calibration fingerprint.

        Фіксує requested model і тексти prompts; зміна будь-якого з них
        потребує нового калібрування, а не повторного використання labels.
        """
        self.client = client
        directory = root / "prompts/rag/judge-v1"
        self.correct_prompt = (directory / "correct.txt").read_text(encoding="utf-8")
        self.faithful_prompt = (directory / "faithful.txt").read_text(encoding="utf-8")
        self.identity = digest({"model": client.model, "correct": self.correct_prompt,
                                "faithful": self.faithful_prompt, "schema": "rag-eval-1"})

    def correct(self, case, answer) -> tuple[bool, str]:
        """Порівнює відповідь із ручним reference за змістом, не raw strings.

        Reference надсилається тільки цьому судді. Невалідний judge JSON
        поширює помилку: caller має позначити run incomplete.
        """
        payload = {"question": case.question, "reference": case.reference, "expected_no_answer": not case.answerable,
                   "answer": answer.model_dump(mode="json")}
        messages = [{"role": "system", "content": self.correct_prompt},
                    {"role": "user", "content": canonical_json(payload)}]
        verdict = Verdict.model_validate_json(self.client.call(messages, structured_format(Verdict, "correctness")))
        return verdict.correct, verdict.reason

    def faithful(self, answer, selected: dict) -> tuple[bool | None, list[dict]]:
        """Перевіряє атомарні факти саме проти наведених контекстних джерел.

        Не отримує reference. Для чесного not_found не викликає LLM.
        Unknown citations або порожні докази supported claim дають
        incomplete, а хоча б одна unsupported claim — False.
        """
        if answer.status == "not_found":
            return None, []
        claims = [{"claim_index": index, "text": claim.text, "sources": [{"chunk_id": i, "text": selected[i].text}
                  for i in claim.chunk_ids]} for index, claim in enumerate(answer.claims)]
        payload = {"claims": claims, "limitations": answer.limitations}
        messages = [{"role": "system", "content": self.faithful_prompt},
                    {"role": "user", "content": canonical_json(payload)}]
        response = Faithfulness.model_validate_json(self.client.call(messages, structured_format(Faithfulness, "faithfulness")))
        if {c.claim_index for c in response.claims} != set(range(len(answer.claims))):
            raise ValueError("judge_incomplete: не всі твердження оцінено")
        if any(set(c.chunk_ids) - set(answer.claims[c.claim_index].chunk_ids)
               or (c.supported and not c.chunk_ids) for c in response.claims):
            raise ValueError("judge_incomplete: невалідні докази")
        return all(c.supported for c in response.claims), [c.model_dump(mode="json") for c in response.claims]
