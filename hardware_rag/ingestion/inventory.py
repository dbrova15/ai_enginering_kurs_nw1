"""Підготовка конкретних кандидатів корпусу; не затверджує їх замість людини."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from ..artifacts import file_digest, read_json, write_json

# Офіційні datasheets доповнюють HTML-статті другим реальним форматом.
PDF_CANDIDATES = [
    ("ESP32", "https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf"),
    ("ESP32-S3", "https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf"),
    ("ESP8266", "https://www.espressif.com/sites/default/files/documentation/esp8266-technical_reference_en.pdf"),
    ("STM32F103C8", "https://www.st.com/resource/en/datasheet/stm32f103c8.pdf"),
    ("STM32F103VD", "https://www.st.com/resource/en/datasheet/stm32f103vd.pdf"),
]
# Обмеження захищає read-only інвентаризацію від випадкового великого архіву.
MAX_DOCUMENT_BYTES = 40 * 1024 * 1024


def inventory(root: Path, destination: Path | None = None) -> dict:
    """Отримує article URLs, резервні статті та 5 datasheets для ручного review.

    Зберігає нові originals у .rag/corpus-candidates, а source draft —
    у data/hw2. Не змінює TXT ДЗ1, не виставляє approved і не переносить
    невідомі дати/версії з URL як нібито підтверджені metadata.
    """
    manifest = read_json(root / "data/sourses/hm1/manifest.json")
    proposals = [{"source_id": r["id"], "url": r["article_url"], "title": r["title"],
                  "language": r["language"], "format": "html"} for r in manifest]
    existing = {p["source_id"] for p in proposals}
    reserve = [r for r in read_json(root / "data/sourses/all_text/manifest.json")
               if r["language"] == "uk" and r["id"] not in existing][:10]
    proposals += [{"source_id": r["id"], "url": r["article_url"], "title": r["title"],
                   "language": r["language"], "format": "html"} for r in reserve]
    proposals += [{"source_id": "DS-" + name, "url": url, "title": name + " technical documentation",
                   "language": "en", "format": "pdf"} for name, url in PDF_CANDIDATES]
    directory = root / ".rag/corpus-candidates"
    directory.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda item: _fetch(item, directory, root), proposals))
    sources = [r["source"] for r in results if "source" in r]
    output = {"review_status": "draft", "sources": sources,
              "errors": [r for r in results if "source" not in r]}
    write_json(destination or root / "data/hw2/sources.draft.json", output)
    return {"downloaded": len(sources), "errors": output["errors"]}


def _fetch(proposal: dict, directory: Path, root: Path) -> dict:
    """Завантажує одного публічного кандидата, перевіряючи HTTP і тип байтів.

    Нові файли створює без перезапису; повторно існуючий файл читає як
    локальну кандидатуру. Помилка лишається в audit й не зараховується
    як успішний документ. Текст HTML selector ще потребує перевірки.
    """
    import httpx
    path = directory / f"{proposal['source_id']}.{proposal['format']}"
    try:
        if not path.exists():
            with httpx.stream("GET", proposal["url"], follow_redirects=True, timeout=40,
                              headers={"User-Agent": "HardwareResearch-course/2.0"}) as response:
                response.raise_for_status()
                data = bytearray()
                for block in response.iter_bytes():
                    data.extend(block)
                    if len(data) > MAX_DOCUMENT_BYTES:
                        raise ValueError("document_too_large")
            if proposal["format"] == "pdf" and not data.startswith(b"%PDF"):
                raise ValueError("not_pdf")
            with path.open("xb") as stream:
                stream.write(data)
        selector = _selector(path) if proposal["format"] == "html" else None
        source = {**proposal, "path": path.relative_to(root).as_posix(),
                  "raw_sha256": file_digest(path), "selector": selector,
                  "review_status": "draft", "redistribution": "Публічне джерело; право поширення потребує review"}
        return {"source": source}
    except (httpx.HTTPError, OSError, ValueError) as error:
        return {"source_id": proposal["source_id"], "url": proposal["url"], "error": type(error).__name__}


def _selector(path: Path) -> str | None:
    """Вибирає кандидатний selector із відомих контентних контейнерів.

    Перевірка ≥500 символів відсікає порожню оболонку; вона не доводить
    правильність extraction. Фінальний selector підтверджується QA.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    for selector in ("article", "main", "[itemprop='articleBody']", ".article-content", ".entry-content",
                     ".post-content", ".art_content", ".aux-pages", "#article", ".article"):
        node = soup.select_one(selector)
        if node and len(node.get_text()) >= 500:
            return selector
    return None
