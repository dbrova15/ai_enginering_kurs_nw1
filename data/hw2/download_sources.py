"""Відтворюване отримання погоджених originals без перезапису чи зміни hashes."""

import hashlib
import sys
from pathlib import Path

# Дозволяє запускати цей скрипт із кореня, не встановлюючи власний пакет через pip.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from hardware_rag.artifacts import file_digest, within
from hardware_rag.ingestion.pipeline import source_records

# Такі самі межі bytes, як у read-only інвентаризації публічних документів.
MAX_BYTES = 40 * 1024 * 1024


def download() -> None:
    """Отримує лише URLs approved-реєстру й перевіряє зафіксовані SHA-256.

    Змінений сайт/HTTP-помилка блокують відтворення, не оновлюють corpus.
    Існуючий правильний original не завантажується повторно. Повний текст
    лишається локально; публікація його прав цим не підтверджується.
    """
    import httpx
    for source in source_records(ROOT / "data/hw2/sources.json"):
        path = within(ROOT, source.path)
        if path.exists():
            if file_digest(path) != source.raw_sha256:
                raise ValueError(f"Existing source hash mismatch: {source.source_id}")
            continue
        data = bytearray()
        with httpx.stream("GET", source.url, follow_redirects=True, timeout=60,
                          headers={"User-Agent": "HardwareResearch-course/2.0"}) as response:
            response.raise_for_status()
            for block in response.iter_bytes():
                data.extend(block)
                if len(data) > MAX_BYTES:
                    raise ValueError("Source перевищує дозволений розмір")
        if hashlib.sha256(data).hexdigest() != source.raw_sha256:
            raise ValueError(f"Source changed: {source.source_id}; не приймайте нові байти без review")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
        print(source.source_id, "OK")


if __name__ == "__main__":
    download()
