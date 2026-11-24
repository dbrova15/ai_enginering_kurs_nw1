"""Малі контрольовані дані офлайн-тестів; не видаються за корпус чи LLM-якість."""

from types import SimpleNamespace
from hardware_rag.documents import Block, Chunk, Source
from hardware_rag.answers import Attempt


def source(**updates):
    """Створює синтетичне approved-джерело тільки для unit fixtures.

    URL example.invalid не завантажується. Явний тестовий статус
    не змінює й не затверджує жодного реального source registry.
    """
    values = dict(source_id="test", path="test.html", url="https://example.invalid/test",
                  title="Test device", format="html", language="uk", raw_sha256="a" * 64,
                  document_version="1.0", version_status="known", review_status="approved")
    return Source(**(values | updates))


def chunk(identifier="c1", text="ESP32 supports Wi-Fi at 3.3 V.", **updates):
    """Повертає невеликий Chunk із proof span та локальними aliases.

    ID навмисно простий для перевірки ranking/citation логіки; цими
    даними не вимірюється реальний retrieval HardwareResearch.
    """
    values = dict(chunk_id=identifier, document_id="d", dataset_id="dataset", content_sha256="d",
                  text=text, title="Test", section="Power", language="uk", aliases=[source()],
                  spans=[("b1", 0, len(text))])
    return Chunk(**(values | updates))


class Words:
    """Детермінований лічильник слів для тестування меж без model weights.

    Це явний test double, не production tokenizer і не оцінка token cost.
    metadata входить у fingerprints, щоб не змішати його з реальним E5.
    """
    def __init__(self):
        """Позначає tokenizer як synthetic та створює мінімальний fingerprint.

        Відсутні будь-які завантаження, cache або звернення до реального
        model registry, тому unit suite може працювати на чистому runner.
        """
        self.metadata = {"synthetic_test_tokenizer": True}

    def count(self, text):
        """Рахує whitespace-слова для передбачуваних unit expectations.

        Повертає integer; caller не може використати цей об'єкт як
        підтверджений tokenizer профіль у справжньому model evaluation.
        """
        return len(text.split())

    def passage(self, title, section, text):
        """Комбінує prefix, metadata й текст як у виробничому адаптері.

        Це дозволяє перевірити врахування заголовків у hard cap без
        залежності від конкретного tokenizer.json чи його словника.
        """
        return f"passage: {title} / {section}\n{text}"

    def fits(self, title, section, text, cap):
        """Перевіряє повне тестове passage з metadata проти cap.

        Порожній текст не є допустимим доказом, навіть якщо count=0.
        Метод не обрізає текст, щоб відсутні spans були помітні тестам.
        """
        return bool(text.strip()) and self.count(self.passage(title, section, text)) <= cap

    def query(self, question, cap):
        """Перевіряє тестовий запит і додає один query-prefix.

        Відтворює правило помилки для порожнього/задовгого питання,
        не оцінюючи реальну модельну довжину.
        """
        if not question.strip() or self.count(question) > cap:
            raise ValueError("bad query")
        return "query: " + question


class FakeEmbedding:
    """Контрольовані 3D-вектори для перевірки Qdrant і metadata-фільтрів.

    Текст із Wi-Fi спрямований по першій осі, решта — по другій.
    Це аналітичний тест індексу, а не семантична embedding-модель.
    """
    # Менша dimension робить очікувані cosine similarities зрозумілими в тесті.
    dimension = 3

    def __init__(self):
        """Створює synthetic model fingerprint без inference чи мережі.

        Fingerprint навмисно відрізняється від виробничих model assets,
        тож fake index не можна випадково прийняти як справжній.
        """
        self.metadata = {"synthetic_model": "axes-1"}

    def encode(self, texts):
        """Відображає тексти в точно відомі вектори для ранжування.

        Повертає один вектор на input у тому самому порядку; шуму та
        випадковості немає, тому збої вказують на код, а не LLM.
        """
        return [[1.0, 0.0, 0.0] if "wi-fi" in t.casefold() else [0.0, 1.0, 0.0] for t in texts]


class FakeClient:
    """Послідовність JSON-відповідей для перевірки primary/repair pipeline.

    Не створює SDK-клієнта й не читає .env. Кожний виклик має реєстр
    attempts, щоб pipeline можна було перевірити без зовнішньої мережі.
    """
    def __init__(self, responses):
        """Запам'ятовує явну скінченну послідовність JSON або exceptions.

        Після вичерпання тест має впасти; прихований необмежений retry
        не може пройти завдяки нескінченному mock generator.
        """
        self.responses = iter(responses)
        self.attempts = []
        self.messages = []

    def call(self, messages, schema, *, kind="primary"):
        """Видає наступну відповідь і записує kind/status без справжнього API.

        Зберігає messages для перевірки відсутності reference leakage.
        Exception у fixture відтворює явну технічну невдачу.
        """
        self.messages.append(messages)
        value = next(self.responses)
        if isinstance(value, Exception):
            raise value
        self.attempts.append(Attempt(kind=kind, status="received", seconds=0.1, content=value))
        return value


def minimal_pdf(texts):
    """Генерує мінімальний справжній PDF із Type1 text для parser tests.

    Підтримує ASCII-рядок на сторінку й коректні xref offsets. Не
    потребує reportlab і не є документом предметного корпусу.
    """
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    page_ids = []
    for text in texts:
        page_id = len(objects) + 1
        page_ids.append(page_id)
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 700 Td ({escaped}) Tj ET".encode("ascii")
        objects += [f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {page_id+1} 0 R >>".encode(),
                    b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"]
    objects[1] = ("<< /Type /Pages /Kids [" + " ".join(f"{i} 0 R" for i in page_ids) + f"] /Count {len(page_ids)} >>").encode()
    output, offsets = bytearray(b"%PDF-1.4\n"), [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    output.extend(b"".join(f"{offset:010} 00000 n \n".encode() for offset in offsets[1:]))
    output.extend(f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(output)
