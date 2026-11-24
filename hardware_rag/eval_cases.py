"""Еталонні записи ДЗ2; імпортуються evaluation, але не generator pipeline."""

from typing import Literal
from pydantic import Field, model_validator
from .documents import StrictRecord


class Evidence(StrictRecord):
    """Ручна адреса доказу всередині нормалізованого вихідного блока.

    Не залежить від випадкового retrieval rank. start/end задають
    напіввідкритий символьний діапазон, що перевіряється проти blocks.json.
    """
    block_id: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)


class EvalCase(StrictRecord):
    """Питання, очікувана поведінка й докази, відділені від LLM input.

    Один кейс може входити у retrieval subset і кілька coverage tags.
    review_status=approved означає реальну людську перевірку змісту,
    а не загальний дозвіл агенту працювати автономно.
    """
    case_id: str
    question: str = Field(min_length=1)
    language: Literal["uk", "en", "ru"]
    filter_language: Literal["uk", "en", "ru"] | None = None
    filter_format: Literal["html", "pdf"] | None = None
    answerable: bool
    reference: str
    relevant: list[str]
    evidence: list[Evidence]
    facts: list[list[str]]
    scoring_mode: Literal["deterministic", "judge"]
    retrieval_member: bool = False
    tags: list[str]
    review_status: Literal["draft", "approved"] = "draft"

    @model_validator(mode="after")
    def consistent_reference(self):
        """Перевіряє no-answer та answerable інваріанти еталону.

        Не доводить фактичну правильність reference — це ручний крок.
        При суперечності в даних відхиляє кейс до викликів моделі.
        """
        if not self.answerable and (self.relevant or self.evidence or self.facts or self.reference or self.retrieval_member):
            raise ValueError("no-answer містить еталонні факти/докази")
        if self.answerable and (not self.relevant or not self.evidence or not self.reference):
            raise ValueError("answerable не має reference/доказів")
        if self.scoring_mode == "deterministic" and self.answerable and not self.facts:
            raise ValueError("deterministic case не має фактів")
        return self


class HumanLabel(StrictRecord):
    """Ручна оцінка конкретної реальної відповіді й контексту за SHA-256.

    Correctness і faithful оцінюються незалежно. Без approved-запису
    приклад не може калібрувати judge для фінального quality gate.
    """
    label_id: str
    case_id: str
    answer_sha256: str
    context_sha256: str
    correct: bool
    faithful: bool | None
    reason: str
    review_status: Literal["draft", "approved"] = "draft"
