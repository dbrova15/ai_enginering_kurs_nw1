"""Налаштування RAG без секретів; усі шляхи обмежені workspace."""

from pathlib import Path
from typing import Literal
from pydantic import Field, model_validator
from .artifacts import read_json, within
from .documents import StrictRecord

# Корінь визначається місцем пакета, а не поточним робочим каталогом оболонки.
ROOT = Path(__file__).resolve().parent.parent


class RagConfig(StrictRecord):
    """Повна відтворювана конфігурація алгоритмів без API-ключів.

    Початкові параметри взято зі спеки; вони не є результатом вимірів.
    Платний профіль вимкнено до окремого погодження бюджету й тарифів.
    """
    sources: str = "data/hw2/sources.json"
    processed: str = "data/hw2/processed"
    indexes: str = ".rag/indexes"
    assets: str = ".rag/models"
    testset: str = "evals/hw2/testset.json"
    labels: str = "evals/hw2/labels.json"
    thresholds: str = "evals/hw2/thresholds.json"
    runs: str = "evals/hw2/runs"
    target_tokens: int = Field(default=320, ge=16)
    chunk_cap: int = Field(default=384, ge=32, le=480)
    overlap: int = Field(default=48, ge=0)
    query_cap: int = Field(default=96, ge=8, le=128)
    candidates: int = Field(default=20, ge=5, le=100)
    k: int = Field(default=5, ge=1, le=20)
    rrf_constant: int = Field(default=60, ge=1)
    retrieval: Literal["vector", "hybrid", "hybrid+rerank"] = "hybrid+rerank"
    context_tokens: int = Field(default=3500, ge=128)
    output_tokens: int = Field(default=1200, ge=64, le=16384)
    model_context_tokens: int = Field(default=128000, ge=512, le=128000)
    tokenizer_encoding: str = "o200k_base"
    generator_prompt: str = "prompts/rag/v1/system.txt"
    timeout_seconds: float = Field(default=60.0, gt=0, allow_inf_nan=False)
    transport_retries: int = Field(default=2, ge=0, le=2)
    paid_enabled: bool = False
    budget_usd: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    input_usd_per_million: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    output_usd_per_million: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    pricing_date: str | None = None
    pricing_provider: Literal["openai", "openrouter", "ollama"] | None = None
    price_source: str | None = None

    @model_validator(mode="after")
    def consistent_limits(self):
        """Відхиляє суперечливі ліміти до запуску pipeline чи API.

        Target має вміщатися в cap, overlap — бути меншим за target,
        а кандидатів має вистачати для top-k. Повертає self без змін.
        """
        if self.target_tokens > self.chunk_cap or self.overlap >= self.target_tokens:
            raise ValueError("Несумісні параметри chunking")
        if self.k > self.candidates:
            raise ValueError("k перевищує кількість кандидатів")
        return self

    def path(self, field: str, root: Path = ROOT) -> Path:
        """Повертає безпечний абсолютний шлях для іменованого поля config.

        Приймає тільки наявне рядкове поле; within додатково забороняє
        вихід за workspace. Не застосовується до назв моделей чи URL.
        """
        value = getattr(self, field)
        if not isinstance(value, str):
            raise ValueError("Поле не є шляхом")
        return within(root, value)


def load_config(path: Path | None = None) -> RagConfig:
    """Читає config/hw2.json і валідовує всі поля до побічних ефектів.

    Для явного path не шукає fallback-файлів. Відсутній config є
    помилкою; параметри з секретами сюди ніколи не додаються.
    """
    return RagConfig.model_validate(read_json(path or ROOT / "config/hw2.json"))
