"""PDF extraction: сторінки й таблиці з координатами, без автоматичного OCR."""

from pathlib import Path
from ..documents import Block

# Сторінка з меншою кількістю символів не підтверджує наявності текстового шару.
MIN_PAGE_CHARS = 50

# Максимальний проміжок між символами одного слова у PDF points; 3 зливало
# сусідні слова технічних таблиць ESP32. Менше значення відновлює пробіли
# за геометрією без словникових виправлень або зміни чисел/одиниць.
TEXT_X_TOLERANCE = 1


def extract_pdf(path: Path, audit: list | None = None) -> list[Block]:
    """Витягує читабельний PDF у блоки з номерами сторінок і таблицями.

    Текст усередині знайденої таблиці вилучається зі звичайного потоку,
    щоб не індексувати його двічі. Скан або порожня сторінка без таблиці
    позначається в audit; весь документ без придатного текстового шару
    викликає needs_ocr-помилку. Назви невідомих розділів не вигадуються.
    Кеші сторінок звільняються одразу після обробки, щоб пам'ять не росла
    пропорційно всім char/layout objects багатосторінкового datasheet.
    """
    import pdfplumber
    blocks = []
    total_characters = 0
    with pdfplumber.open(path) as document:
        repeated = _repeated_margins(document.pages)
        for number, page in enumerate(document.pages, 1):
            # Рамка схеми з одним рядком/стовпцем не є таблицею з заголовками.
            tables = [table for table in page.find_tables()
                      if len(table.extract()) > 1
                      and any(sum(bool(cell) for cell in row) > 1 for row in table.extract())]
            table_boxes = [table.bbox for table in tables]
            prose = page.filter(lambda obj: not _in_tables(obj, table_boxes))
            lines = prose.extract_text_lines(x_tolerance=TEXT_X_TOLERANCE) or []
            entries = []
            for line in lines:
                text = line["text"]
                if "(cid:" in text:
                    if audit is not None:
                        audit.append(f"undecodable_graphic_text:{number}; див. оригінал PDF")
                    continue
                if _margin_key(text) in repeated and (line["top"] < 65 or line["bottom"] > page.height - 65):
                    continue
                entries.append((line["top"], "paragraph", text))
            for table in tables:
                rows = _table_rows(table)
                # Об'єднаний підпис над колонками — окремий prose block, не header.
                header_index = next(i for i, row in enumerate(rows) if sum(bool(cell) for cell in row) > 1)
                for index, row in enumerate(rows[:header_index]):
                    caption = " ".join(cell for cell in row if cell)
                    if "(cid:" not in caption and caption.strip():
                        entries.append((table.bbox[1] + index / 1000, "paragraph", caption))
                rows = rows[header_index:]
                text = "\n".join(" | ".join((cell or "").replace("\n", " ") for cell in row) for row in rows)
                if "(cid:" in text:
                    if audit is not None:
                        audit.append(f"undecodable_table:{number}; потрібен ручний перегляд оригіналу")
                    continue
                entries.append((table.bbox[1], "table", text))
            count = sum(len(text) for _, _, text in entries)
            total_characters += count
            if count < MIN_PAGE_CHARS and audit is not None:
                audit.append(f"low_text_page:{number}; зображення не інтерпретовано")
            for _, kind, text in sorted(entries):
                if text.strip():
                    ordinal = len(blocks)
                    blocks.append(Block(block_id=str(ordinal), ordinal=ordinal, kind=kind, text=text,
                                        section=f"Сторінка {number}; розділ не визначено",
                                        page_start=number, page_end=number))
            page.close()
    if total_characters < MIN_PAGE_CHARS:
        raise ValueError("needs_ocr: документ не має придатного текстового шару")
    return blocks


def _in_tables(obj: dict, boxes: list) -> bool:
    """Визначає, чи центр символу належить bounding box будь-якої таблиці.

    Об'єкти без координат не вилучає. Це координатна дедуплікація
    PDF extraction, а не евристика видалення схожих речень.
    """
    if "x0" not in obj or "top" not in obj:
        return False
    x = (obj["x0"] + obj.get("x1", obj["x0"])) / 2
    y = (obj["top"] + obj.get("bottom", obj["top"])) / 2
    return any(left <= x <= right and top <= y <= bottom for left, top, right, bottom in boxes)


def _table_rows(table) -> list[list]:
    """Відновлює значення вертикально об'єднаних клітинок за геометрією PDF.

    None не заповнюється механічно: попередня bbox має реально покривати
    поточний рядок. Так IOH/умови струму зберігаються біля кожного domain,
    але навмисно порожня клітинка нового рядка не успадковує старе значення.
    """
    rows = table.extract(x_tolerance=TEXT_X_TOLERANCE)
    previous = {}
    result = []
    for values, geometry in zip(rows, table.rows):
        filled = list(values)
        top = geometry.bbox[1]
        for column, box in enumerate(geometry.cells):
            if box is not None:
                previous[column] = (box, values[column])
            elif column in previous:
                ancestor, value = previous[column]
                if ancestor[1] <= top < ancestor[3] - 0.01:
                    filled[column] = value
        result.append(filled)
    return result


def _margin_key(text: str) -> str:
    """Уніфікує тільки пробіли для зіставлення повторюваних колонтитулів.

    Числа не стирає, тому різні технічні значення не стають помилково
    однаковими службовими рядками. Не змінює вихідний текст блока.
    """
    return " ".join(text.split())


def _repeated_margins(pages: list) -> set[str]:
    """Знаходить дослівні повтори у верхньому/нижньому полі ≥3 сторінок.

    Для короткого PDF нічого не видаляє. Кандидат має повторюватися
    щонайменше на половині сторінок, а не лише двічі у змісті.
    """
    from collections import Counter
    if len(pages) < 3:
        return set()
    counts = Counter()
    for page in pages:
        counts.update({_margin_key(line["text"]) for line in page.extract_text_lines(x_tolerance=TEXT_X_TOLERANCE) or []
                       if line["top"] < 65 or line["bottom"] > page.height - 65})
        page.close()
    return {text for text, count in counts.items() if count >= max(3, len(pages) / 2)}
