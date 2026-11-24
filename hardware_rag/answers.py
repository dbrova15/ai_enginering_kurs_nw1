"""Контракти відповіді та фактичних спроб без еталонної розмітки."""

from typing import Literal
from pydantic import Field, model_validator
from .documents import StrictRecord


class Claim(StrictRecord):
    """Твердження та IDs доказів, які модель повинна пов'язати з ним.

    Формальну наявність IDs перевіряє pipeline, семантичну підтримку —
    judge. Валідний JSON сам по собі не доводить правдивість тексту.
    """
    text: str = Field(min_length=1)
    chunk_ids: list[str] = Field(min_length=1)


class Answer(StrictRecord):
    """Зміст LLM-відповіді без журналу, вартості й даних еталону.

    answered/partial потребують claims; not_found забороняє факти.
    Усі три поля обов'язкові для strict structured-output schema.
    """
    status: Literal["answered", "partial", "not_found"]
    claims: list[Claim]
    limitations: str

    @model_validator(mode="after")
    def consistent_status(self):
        """Відхиляє суперечливі статуси та дублікати цитат у claim.

        not_found без claims/limitations відображається стандартною
        фразою, тому в поясненні відмови не можна приховати домисел.
        """
        if self.status == "not_found" and (self.claims or self.limitations):
            raise ValueError("not_found не може містити факти чи довільне пояснення")
        if self.status != "not_found" and not self.claims:
            raise ValueError("Відповідь без тверджень повинна мати статус not_found")
        if self.status == "partial" and not self.limitations.strip():
            raise ValueError("partial має явно пояснювати межу підтверджених даних")
        if any(not c.text.strip() for c in self.claims):
            raise ValueError("Твердження не може містити лише пробіли")
        if any(len(c.chunk_ids) != len(set(c.chunk_ids)) for c in self.claims):
            raise ValueError("Цитата повторюється в одному твердженні")
        return self


class Attempt(StrictRecord):
    """Один transport-виклик, включно з невдалим, первинним і repair.

    Невідомі usage та actual_model лишаються null. error містить
    тільки безпечний тип/status, не сире повідомлення з ключем чи URL.
    """
    kind: Literal["primary", "repair", "retry"]
    status: str
    seconds: float
    content: str | None = None
    error: str | None = None
    actual_model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str | None = None


class Result(StrictRecord):
    """Відділяє технічну невдачу від чесної відповіді not_found.

    selected_ids описує лише реально переданий контекст; answer=null
    означає failed. attempts зберігає первинну відповідь навіть після
    успішного repair, щоб не завищити первинну валідність.
    """
    status: Literal["success", "failed"]
    answer: Answer | None
    selected_ids: list[str]
    attempts: list[Attempt] = Field(default_factory=list)
    error: str | None = None
    seconds: float = 0.0
    first_attempt_valid: bool = False
