"""Обережна нормалізація змісту без зміни чисел, одиниць і коду."""

import re
import unicodedata
from ..artifacts import digest
from ..documents import Block

# Зміна алгоритму нормалізації повинна змінювати ідентичність dataset.
NORMALIZATION_VERSION = "rag-normalize-1"


def normalize_blocks(blocks: list[Block]) -> tuple[str, list[Block]]:
    """Повертає content hash і блоки зі стабільними ID за нормалізованим змістом.

    NFC й LF застосовує до всіх блоків; послідовності пробілів стискає
    лише в прозі. Відступи коду, рядки таблиць, знаки й одиниці зберігає.
    Page/section не визначають тотожність змісту між HTML і PDF-копією.
    """
    cleaned = []
    for block in blocks:
        text = unicodedata.normalize("NFC", block.text).replace("\r\n", "\n").replace("\r", "\n")
        if block.kind not in ("code", "table"):
            text = re.sub(r"[^\S\n]+", " ", text).strip()
        else:
            text = text.strip("\n")
        if text.strip():
            cleaned.append(block.model_copy(update={"text": text, "ordinal": len(cleaned)}))
    if not cleaned:
        raise ValueError("Документ порожній після нормалізації")
    content_hash = digest([{"kind": b.kind, "text": b.text} for b in cleaned])
    normalized = [b.model_copy(update={"block_id": f"{content_hash[:16]}:b{i}"}) for i, b in enumerate(cleaned)]
    return content_hash, normalized
