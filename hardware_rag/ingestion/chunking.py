"""Нарізка за структурою й fixed baseline зі збереженням координат доказів."""

from ..artifacts import digest
from ..documents import Block, Chunk, Source

# Версія алгоритму входить у fingerprint, тому зміна меж не змішує datasets.
CHUNKING_VERSION = "rag-heading-2"


def _take(text: str, fits) -> int:
    """Знаходить найбільший початок тексту, що проходить токенний ліміт.

    Спочатку двійковий пошук за символами, потім відступ до newline
    чи пробілу, якщо така межа близько. Завжди повертає >0 або помилку,
    тому довгий нероздільний блок не спричиняє нескінченного циклу.
    """
    low, high = 1, len(text)
    result = 0
    while low <= high:
        middle = (low + high) // 2
        if fits(text[:middle]):
            result, low = middle, middle + 1
        else:
            high = middle - 1
    if result == 0:
        raise ValueError("Неможливо вмістити непорожній доказ у chunk cap")
    if result < len(text):
        boundary = max(text.rfind("\n", 0, result), text.rfind(" ", 0, result))
        if boundary >= result // 2:
            result = boundary + 1
    return result


def make_chunks(blocks: list[Block], aliases: list[Source], content_hash: str,
                tokens, config, *, fixed: bool = False) -> list[Chunk]:
    """Створює детерміновані чанки; dataset_id заповнює publisher.

    Основний режим групує блоки одного розділу, fixed ріже плаский
    текст із overlap. Обидва режими зберігають spans і hard cap повного
    embedding input; модельний tokenizer можна підмінити лише в тесті.
    """
    title = aliases[0].title
    identity = digest({"version": CHUNKING_VERSION, "fixed": fixed,
                       "target": config.target_tokens, "cap": config.chunk_cap,
                       "overlap": config.overlap, "tokens": tokens.metadata})
    pieces = _fixed_windows(blocks, title, tokens, config) if fixed else _heading_windows(blocks, title, tokens, config)
    chunks = []
    for text, section, spans, pages in pieces:
        identifier = digest({"document": content_hash, "config": identity, "spans": spans})
        chunks.append(Chunk(chunk_id=identifier, document_id=content_hash, dataset_id="pending",
                            content_sha256=content_hash, text=text, title=title, section=section,
                            language=aliases[0].language, aliases=aliases, spans=spans,
                            page_start=min(pages) if pages else None, page_end=max(pages) if pages else None))
    return chunks


def _heading_windows(blocks: list[Block], title: str, tokens, config) -> list:
    """Накопичує блоки одного розділу й ділить тільки надмірно довгі.

    Повертає текст/section/spans/pages для кожного вікна. Таблиці
    розбиваються на рядках, якщо можливо; оригінальний span збережено.
    """
    windows = []
    current = None
    for block in blocks:
        fits = lambda t: tokens.fits(title, block.section, t, config.target_tokens)
        for part, spans in _block_parts(block, fits):
            page = [p for p in (block.page_start, block.page_end) if p is not None]
            if current and current[1] == block.section and fits(current[0] + "\n\n" + part):
                current = (current[0] + "\n\n" + part, current[1], current[2] + spans, current[3] + page)
                windows[-1] = current
            else:
                current = (part, block.section, spans, page)
                windows.append(current)
    return windows


def _block_parts(block: Block, fits) -> list:
    """Ділить довгий блок, зберігаючи рядки коду та заголовок таблиці.

    Для table повторює перший рядок у кожній частині й додає його
    справжній span, а не вигаданий текст. Проза ділиться детерміновано;
    code спершу шукає попередню межу рядка. Усі частини мають exact proof.
    """
    text = block.text
    if fits(text):
        return [(text, [(block.block_id, 0, len(text))])]
    if block.kind == "table" and "\n" in text:
        header_end = text.index("\n") + 1
        header = text[:header_end]
        if not fits(header + "x"):
            raise ValueError("Табличний заголовок не вміщується; потрібна ручна перевірка")
        result, offset = [], header_end
        while offset < len(text):
            remaining = text[offset:]
            if not remaining.strip():
                break
            limit = _take(remaining, lambda part: fits(header + part))
            if limit < len(remaining):
                line = remaining.rfind("\n", 0, limit)
                if line >= 0:
                    limit = line + 1
            result.append((header + remaining[:limit], [(block.block_id, 0, header_end),
                                                        (block.block_id, offset, offset + limit)]))
            offset += limit
        return result
    result, offset = [], 0
    while offset < len(text):
        remaining = text[offset:]
        if not remaining.strip():
            break
        limit = _take(remaining, fits)
        if block.kind == "code" and limit < len(remaining):
            line = remaining.rfind("\n", 0, limit)
            if line >= 0:
                limit = line + 1
        result.append((remaining[:limit], [(block.block_id, offset, offset + limit)]))
        offset += limit
    return result


def _fixed_windows(blocks: list[Block], title: str, tokens, config) -> list:
    """Ріже той самий нормалізований текст fixed-вікнами з exact overlap.

    Перетин діапазону з картою блоків відновлює правильні proof spans,
    навіть якщо вікно перетинає кілька розділів. Потрібно для чесного
    порівняння з heading-стратегією, а не окремого штучного корпусу.
    """
    text = "\n\n".join(b.text for b in blocks)
    mapping, position = [], 0
    for block in blocks:
        mapping.append((position, position + len(block.text), block))
        position += len(block.text) + 2
    result, start = [], 0
    while start < len(text):
        intersecting = [b for left, right, b in mapping if right > start]
        section = intersecting[0].section
        fits = lambda t: tokens.fits(title, section, t, config.target_tokens)
        end = start + _take(text[start:], fits)
        spans, pages = [], []
        for left, right, block in mapping:
            a, b = max(start, left), min(end, right)
            if a < b:
                spans.append((block.block_id, a - left, b - left))
                pages.extend(p for p in (block.page_start, block.page_end) if p is not None)
        if spans and text[start:end].strip():
            result.append((text[start:end], section, spans, pages))
        if end == len(text):
            break
        overlap = end
        while overlap > start and tokens.count(text[overlap - 1:end]) <= config.overlap:
            overlap -= 1
        start = max(start + 1, overlap + 1)
    return result
