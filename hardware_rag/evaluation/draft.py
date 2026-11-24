"""Прозора чернетка тестсету з точними доказами; не замінює ручну розмітку."""

import re
from pathlib import Path
from ..artifacts import read_json, write_json

# Питання прив'язані до власних джерел; regex знаходить доказові уривки,
# а не підлаштовує еталон під model outputs/rankings. Кілька expressions
# означають, що reference має включати докази кожної частини питання.
DRAFT_QUESTIONS = [
    ("HR-0056", "Яке живлення потрібне LCD-шилду в статті про термістор та ADC STM32?", r"LCD.*3[.,]3\s*V", "uk", []),
    ("HR-0055", "Який контролер та інтерфейс використовуються для підключення резистивної сенсорної панелі у другій частині статті про 2.8 TFT LCD і STM32?", r"резистивної сенсорної панелі.*TSC2046.*SPI", "uk", []),
    ("HR-0221", "Як змінюється стан реле при досягненні порогів вимкнення та ввімкнення в описаному термореле з Wi-Fi?", r"Реле увімкнуте.*рівня вимкнення.*рівня увімкнення", "uk", []),
    ("HR-0244", "Як у проєкті моніторингу ваги філаменту використовується Telegram?", r"Telegram|телеграм", "uk", []),
    ("HR-0213", "Яке призначення пристрою для визначення ємності Li-ion акумуляторів?", r"ємност|емкост", "uk", []),
    ("HR-0254", "Який екран використовується у проєкті годинника на Arduino?", r"1602", "uk", []),
    ("HR-0164", "Що дозволяє роботу визначати лінію у проєкті робота на Arduino?", r"датчик|сенсор", "uk", []),
    ("HR-0148", "Скількома двигунами постійного струму та в якому режимі може керувати описана плата драйвера L293D?", r"Плата драйвера двигунів може керувати двома двигунами.*реверсному режимі", "uk", []),
    ("HR-0228", "Як у статті рекомендують підбирати плату BMS для високострумових акумуляторів і чому?", r"Плату BMS підбираємо.*захист.*перегрівалася", "uk", []),
    ("HR-0217", "Які два підходи до програмування ESP32 мовою Python описує стаття?",
     (r"^Zerynth Studio\s*-\s*це потужний", r"^MicroPython\s*-\s*це реалізація мови Python3"), "uk", []),
    ("HR-0001", "Какова задача робота в соревновании mini Sumo?", r"вытолк|виштовх|пол[ея]", "ru", []),
    ("HR-0068", "Что обнаруживает модуль SW-520D?", r"(?:датчик|реагир|чувствител).*(?:наклон|вибрац)", "ru", []),
    ("DS-ESP32", "How much ROM is specified for the ESP32 series?", r"448.*ROM", "en", []),
    ("DS-ESP32-S3", "Which CPU core architecture is specified for ESP32-S3?", r"LX7", "en", ["similar_model"]),
    ("DS-STM32F103C8", "Які обсяги Flash наведені для medium-density STM32F103x8/xB?", r"64\s*or\s*128\s*KB.*Flash", "uk", ["similar_model"]),
    ("DS-STM32F103VD", "Які обсяги Flash наведені для high-density STM32F103xC/xD/xE?", r"256.*512.*Flash", "uk", []),
    ("DS-ESP32", "Яка версія саме наданого datasheet ESP32: 4.9 чи 5.3? Не роби висновку про всі зовнішні джерела.", r"Version\s*5\.3", "uk", ["outdated_version"]),
    ("DS-ESP32-S3", "Чи правильно називати наданий datasheet ESP32-S3 версією 1.0, чи в ньому зазначено 2.2?", r"Version\s*2\.2", "uk", ["outdated_version"]),
]


def make_draft(manifest: dict, chunks: list, blocks: list[dict], destination: Path) -> dict:
    """Створює ≥20 draft-кейсів із source-backed reference та proof spans.

    Evidence вибирає тільки з реально наявного normalized block і його
    chunk span; невдалий regex є помилкою підготовки, не вигаданим proof.
    Для складеного питання вимагає окремий proof кожної expression;
    reference та evidence містять усі ці частини, а relevant — їх union.
    Усі кейси лишаються draft незалежно від дозволу на автономну роботу.
    """
    by_block = {b["block_id"]: b for b in blocks}
    cases = []
    for index, (source_id, question, expression, language, tags) in enumerate(DRAFT_QUESTIONS):
        expressions = (expression,) if isinstance(expression, str) else expression
        proofs = [_evidence(chunks, by_block, source_id, part) for part in expressions]
        reference = "\n\n".join(by_block[block_id]["text"][start:end]
                                for _, block_id, start, end, _ in proofs)
        relevant = sorted({identifier for _, _, _, _, identifiers in proofs for identifier in identifiers})
        evidence = [{"block_id": block_id, "start": start, "end": end}
                    for _, block_id, start, end, _ in proofs]
        cases.append({"case_id": f"hr-q{index+1:02d}", "question": question, "language": language,
                      "filter_language": None, "filter_format": "pdf" if source_id.startswith("DS-") else None,
                      "answerable": True, "reference": reference, "relevant": relevant,
                      "evidence": evidence,
                      "facts": [], "scoring_mode": "judge", "retrieval_member": index < 15,
                      "tags": tags or ["technical"], "review_status": "draft"})
    for index, question in enumerate(("Яка офіційна кількість GPIO у вигаданого контролера HR-Z9999?",
                                      "Яку гарантійну вартість доставки HR-Z9999 до Антарктиди встановлює цей корпус?"), 19):
        cases.append({"case_id": f"hr-q{index:02d}", "question": question, "language": "uk",
                      "filter_language": None, "filter_format": None, "answerable": False, "reference": "",
                      "relevant": [], "evidence": [], "facts": [], "scoring_mode": "judge",
                      "retrieval_member": False, "tags": ["no_answer"], "review_status": "draft"})
    data = {"schema_version": "rag-eval-1", "dataset_id": manifest["dataset_id"],
            "review_status": "draft", "cases": cases}
    write_json(destination, data)
    return data


def _evidence(chunks: list, blocks: dict, source_id: str, expression: str) -> tuple:
    """Знаходить конкретний chunk span, який містить потрібний буквальний proof.

    Канонічний proof обирається в порядку самого документа, а не за
    довжиною довільного блока. Усі regex-збіги є кандидатами relevant,
    але семантичну достатність кожного має перевірити людина. Метод
    не читає rankings чи результати моделі; статус лишається draft.
    """
    candidates = []
    for chunk in chunks:
        if not any(source.source_id == source_id for source in chunk.aliases):
            continue
        for block_id, start, end in chunk.spans:
            text = blocks[block_id]["text"][start:end]
            if re.search(expression, text, re.IGNORECASE):
                priority = (blocks[block_id]["kind"] == "heading", blocks[block_id]["ordinal"], start, chunk.chunk_id)
                candidates.append((priority, chunk, block_id, start, end))
    if not candidates:
        raise ValueError(f"Доказ не знайдено: {source_id}; {expression}")
    _, chunk, block_id, start, end = sorted(candidates, key=lambda item: item[0])[0]
    relevant = sorted({item[1].chunk_id for item in candidates})
    return chunk, block_id, start, end, relevant


def write_review(data: dict, chunks: list, destination: Path) -> None:
    """Рендерить питання/reference/source links для незалежної людської перевірки.

    Не змінює review_status та не заповнює human labels. Це навчальна
    форма review, а не нова версія еталону чи результат калібрування.
    """
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    lines = ["# Ручна перевірка тестсету ДЗ2", "", "Статус: draft; агент не підтверджує ручну перевірку.",
             "", f"Dataset: `{data['dataset_id']}`", "", "| Кейс | Питання | Джерело | Reference |",
             "| --- | --- | --- | --- |"]
    for case in data["cases"]:
        source = by_id[case["relevant"][0]].aliases[0] if case["relevant"] else None
        label = source.title if source else "Очікується відсутність доказу"
        url = source.url if source else ""
        reference = case["reference"].replace("\n", " ").replace("|", "/")
        lines.append(f"| {case['case_id']} | {case['question']} | [{label.replace('|', '/')}]({url}) | {reference} |")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
