"""Строгі типи походження й структури документів, незалежні від еталонів."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

# Версія формату чанків відділяє RAG від контракту DevicePosting ДЗ1.
CHUNK_VERSION = "rag-chunks-1"


class StrictRecord(BaseModel):
    """Базовий контракт без невідомих полів і прихованих перетворень типів.

    Спільний для локальних JSON та відповідей LLM. Неправильний тип
    відхиляється, а не перетворюється: рядок не замінює число чи bool.
    """
    # Єдина сувора політика валідації нових форматів ДЗ2.
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)


class Source(StrictRecord):
    """Один оригінал у реєстрі корпусу з контрольними байтами й provenance.

    path відносний до workspace, hash фіксує очікувані байти. Невідомі
    дата/версія — null. draft не допускається до приймального ingestion;
    людина має перевірити зміст і право поширення originals/chunks.
    """
    source_id: str = Field(min_length=1)
    path: str
    url: str
    title: str
    format: Literal["html", "pdf"]
    language: Literal["uk", "en", "ru"]
    raw_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    published_at: str | None = None
    document_version: str | None = None
    document_family: str | None = None
    version_status: Literal["known", "unknown"] = "unknown"
    redistribution: str = "Потребує перевірки людиною"
    selector: str | None = None
    review_status: Literal["draft", "approved"] = "draft"

    @model_validator(mode="after")
    def consistent_version(self):
        """Відхиляє known без фактичного номера версії джерела.

        Відома дата не означає відому версію. Для невідомої версії
        значення повинно лишатися null, не випадковим припущенням.
        """
        if (self.version_status == "known") != bool(self.document_version):
            raise ValueError("version_status суперечить document_version")
        return self


class Block(StrictRecord):
    """Структурний фрагмент із порядком читання, розділом і сторінками PDF.

    Тип розрізняє prose, heading, list, table й code. Координати proof
    вказуються через block_id та offsets; текст коду зберігає відступи,
    таблиця — зв'язки колонок, невідомий розділ не вигадується.
    """
    block_id: str
    ordinal: int = Field(ge=0)
    kind: Literal["heading", "paragraph", "list", "table", "code"]
    text: str
    section: str
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)


class Chunk(StrictRecord):
    """Одиниця пошуку з текстом, усіма source aliases і доказовими spans.

    spans — трійки (block_id, start, end) у символах нормалізованих
    блоків. Вони дозволяють перевіряти proof після зміни chunking.
    dataset_id і content hash захищають від змішування різних наборів.
    """
    schema_version: Literal["rag-chunks-1"] = CHUNK_VERSION
    chunk_id: str
    document_id: str
    dataset_id: str
    content_sha256: str
    text: str
    title: str
    section: str
    language: Literal["uk", "en", "ru"]
    aliases: list[Source] = Field(min_length=1)
    spans: list[tuple[str, int, int]] = Field(min_length=1)
    page_start: int | None = None
    page_end: int | None = None

    @model_validator(mode="after")
    def valid_spans(self):
        """Перевіряє непорожні невід'ємні spans і повертає self.

        Повну належність меж вихідному тексту перевіряє dataset lint,
        бо Block-оригінали навмисно не дублюються в кожному чанку.
        """
        if any(start < 0 or end <= start for _, start, end in self.spans):
            raise ValueError("Неприпустимий діапазон доказу")
        return self

    def source_for(self, document_format: str | None = None) -> Source:
        """Вибирає source alias відповідного формату або повертає помилку.

        За відсутності фільтра вибір стабільний за source_id. Ніколи
        не підставляє HTML-посилання замість запитаного PDF.
        """
        matches = [s for s in self.aliases if document_format is None or s.format == document_format]
        if not matches:
            raise ValueError("Чанк не має джерела потрібного формату")
        return sorted(matches, key=lambda s: s.source_id)[0]
