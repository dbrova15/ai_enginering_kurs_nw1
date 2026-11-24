"""HTML-парсер зі збереженням порядку списків, таблиць і коду."""

from pathlib import Path
import re
from ..documents import Block

# Ці вузли є службовими елементами сторінки, а не доказами технічного змісту.
BOILERPLATE = "script,style,nav,footer,header,noscript,.cookie,#cookie-banner,.date,.author,.comments"
# Структурні елементи обходяться зверху вниз; вкладені повтори пропускаються.
BLOCK_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "table", "pre")
# BS4 стискає whitespace-only text nodes до пробілу, зокрема перед inline
# span. Для legacy <p>-коду це змінило б tabs ще до нашого classifier.
PRESERVE_WHITESPACE_TAGS = {"pre", "textarea", "p"}
# Старі статті загортають кожний рядок Arduino/C у <p> замість <pre>.
# Явні синтаксичні prefixes дозволяють зберегти string literals/відступи;
# це не виконання коду або спроба виправити його помилки.
CODE_PARAGRAPH = re.compile(
    r"^(?:#\s*(?:include|define|if|ifdef|ifndef|endif|else|pragma)\b|//|/\*|[{}]|"
    r"(?:void|const|int|float|double|char|byte|bool|unsigned|long|auto|struct)\b|"
    r"(?:if|while|for|switch)\s*\(|else(?:\s*\{|\s+if\b|\s+[A-Za-z_]\w*\s*\()|return\b.*;|"
    r"B[01]{4,}\s*,|[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\s*(?:\(|[+*/-]?=|\+\+|--)|"
    r"[A-Z]\w+\s+[A-Za-z_]\w*\s*\()")


def extract_html(path: Path, selector: str | None = None) -> list[Block]:
    """Перетворює локальний HTML на впорядковані типізовані блоки.

    selector дозволяє явно вибрати article для конкретного сайту.
    За його відсутності бере article/main, але не весь boilerplate body.
    Не завантажує ресурси сторінки й не виконує JavaScript.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(path.read_bytes(), "html.parser", preserve_whitespace_tags=PRESERVE_WHITESPACE_TAGS)
    for node in soup.select(BOILERPLATE):
        node.decompose()
    main = soup.select_one(selector) if selector else soup.find("article") or soup.find("main")
    if main is None:
        raise ValueError("HTML потребує явного selector основного змісту")
    sections = []
    blocks = []
    for node in main.find_all(BLOCK_TAGS):
        if _nested_in_block(node, main):
            continue
        name = node.name
        if name.startswith("h"):
            level = int(name[1])
            sections = sections[:level - 1] + [node.get_text(" ", strip=True)]
            kind, text = "heading", sections[-1]
        elif name == "table":
            kind = "table"
            rows = [" | ".join(c.get_text(" ", strip=True) for c in row.find_all(["th", "td"]))
                    for row in node.find_all("tr")]
            text = "\n".join(rows)
        elif name == "pre":
            kind, text = "code", node.get_text()
        elif name == "p":
            kind, text = _paragraph(node)
        else:
            kind = "list" if name == "li" else "paragraph"
            text = node.get_text(" ", strip=True)
        if text.strip():
            ordinal = len(blocks)
            blocks.append(Block(block_id=str(ordinal), ordinal=ordinal, kind=kind, text=text,
                                section=" / ".join(sections) or "Розділ не визначено"))
    if not blocks:
        raise ValueError("HTML не містить придатного тексту")
    return blocks


def _paragraph(node) -> tuple[str, str]:
    """Відділяє очевидний код у legacy <p> від звичайного прозового абзацу.

    Класифікує лише абзаци, де кожний непорожній рядок має code prefix.
    Raw text зберігає пробіли в literals і відступи; <br> дає newline,
    inline spans не вставляють додаткових символів. Невпевнені випадки
    лишаються прозою, без вигадування чи виконання коду.
    """
    from bs4 import Comment, NavigableString
    raw = "".join(str(item) if isinstance(item, NavigableString) and not isinstance(item, Comment)
                  else "\n" if getattr(item, "name", None) == "br" else "" for item in node.descendants)
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if lines and all(CODE_PARAGRAPH.match(line) for line in lines):
        return "code", raw.strip("\r\n")
    return "paragraph", node.get_text(" ", strip=True)


def _nested_in_block(node, main) -> bool:
    """Відсікає повторні дочірні вузли лише ВСЕРЕДИНІ вибраного article.

    Старі сайти використовують table для загального layout. Такий
    зовнішній предок не є таблицею статті й не повинен прибрати весь
    її текст. Обхід зупиняється на межі main, не йде до кореня HTML.
    """
    for parent in node.parents:
        if parent is main:
            break
        if parent.name in ("pre", "table", "li"):
            return True
    return False
