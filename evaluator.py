"""Офлайн-оцінювання збережених відповідей Schema v2 на golden set."""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from main import DevicePosting, GOLDEN, RESULTS, SCHEMA_VERSION

EVALUATOR_VERSION = "schema-v2-exact-set-v1"
FIELDS = tuple(DevicePosting.model_fields)
LIST_FIELDS = ("mentioned_platforms", "mentioned_interfaces")
CONFIG_FIELDS = ("schema_version", "model", "prompt_version", "prompt_sha256",
                 "sampling", "preparation_version")


def index_records(records: list[dict], source: str) -> dict[str, dict]:
    """Упорядковує записи так, щоб кожен можна було знайти за ID статті.

    Отримує список записів і назву джерела для повідомлень про помилки.
    Перевіряє, що кожен запис має непорожній ID і що ID не повторюються.
    Повертає відповідність «ID → запис». Дублікат зупиняє оцінювання:
    інакше одна відповідь могла б непомітно замінити іншу.
    """
    indexed = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"{source}: запис має бути об'єктом")
        document_id = record.get("document_id")
        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError(f"{source}: відсутній document_id")
        if document_id in indexed:
            raise ValueError(f"{source}: дубльований document_id {document_id}")
        indexed[document_id] = record
    return indexed


def load_golden(path: Path) -> dict[str, dict]:
    """Читає файл із правильними відповідями, з якими порівнюватимемо модель.

    Перевіряє формат Schema v2, наявність записів та унікальність ID,
    відсутність повторів у списках і наявність контрольного відбитка джерела.
    Повертає еталони за ID статей. Перевіряє структуру даних, а не істинність
    розмітки: правильність відповідей має підтвердити людина.
    """
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise ValueError("Golden має бути непорожнім JSON-масивом")
    indexed = index_records(records, str(path))
    for document_id, record in indexed.items():
        if record.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"Golden {document_id}: потрібна Schema {SCHEMA_VERSION}")
        expected = DevicePosting.model_validate(record.get("expected"), strict=True)
        for field in LIST_FIELDS:
            values = getattr(expected, field)
            if len(values) != len(set(values)):
                raise ValueError(f"Golden {document_id}: дублікати в {field}")
        if not isinstance(record.get("source_sha256"), str) or not record["source_sha256"]:
            raise ValueError(f"Golden {document_id}: відсутній source_sha256")
    return indexed


def load_run(path: Path) -> list[dict]:
    """Читає результати одного запуску: кожен рядок JSONL — окремий запис.

    Пропускає порожні рядки та повертає список прочитаних записів.
    Якщо рядок неможливо прочитати як JSON, повідомляє назву файлу й номер
    рядка. Порожній файл теж є помилкою. Якість відповідей тут не оцінюється.
    """
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{number}: некоректний JSON") from error
    if not records:
        raise ValueError(f"{path}: немає результатів")
    return records


def run_configuration(records: list[dict]) -> dict:
    """Перевіряє, що всі записи отримано за однакових умов запуску.

    Бере модель, промпт, його відбиток та налаштування з першого запису
    й звіряє їх з рештою. Повертає ці спільні налаштування.
    Неповні дані, інша схема або змішані умови зупиняють оцінювання,
    щоб один показник не об'єднував різні експерименти.
    """
    if not records:
        raise ValueError("Прогін не містить записів")
    configuration = {field: records[0].get(field) for field in CONFIG_FIELDS}
    if any(value is None for value in configuration.values()):
        raise ValueError("Неповні метадані конфігурації прогону")
    if configuration["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"Evaluator підтримує лише Schema {SCHEMA_VERSION}")
    if not isinstance(configuration["sampling"], dict):
        raise ValueError("sampling має бути об'єктом")
    for record in records:
        if any(record.get(field) != value for field, value in configuration.items()):
            raise ValueError("В одному JSONL змішані різні конфігурації")
    return configuration


def score_document(document_id: str, golden: dict, record: dict | None) -> dict:
    """Порівнює відповідь моделі на одну статтю з її еталонною відповіддю.

    Звіряє відбиток джерела та перевіряє структуру успішної відповіді.
    Для кожної характеристики записує, чи є точний збіг; у списках порядок
    і повтори не впливають на збіг, але повтори зберігаються як окрема примітка.
    Відсутня, невдала або невалідна відповідь має нуль збігів за всіма полями.
    Повертає очікувані й фактичні дані, збіги, статус і причину помилки.
    Статус valid означає правильну структуру, а не правильність усіх значень.
    """
    expected = golden["expected"]
    actual, error = None, None
    status = "missing" if record is None else "failed"
    if record is not None:
        if record.get("source_sha256") != golden["source_sha256"]:
            raise ValueError(f"{document_id}: source_sha256 не відповідає golden")
        if not isinstance(record.get("input_sha256"), str) or not record["input_sha256"]:
            raise ValueError(f"{document_id}: відсутній input_sha256")
        result = record.get("result")
        if isinstance(result, dict) and result.get("ok") is True and result.get("status") == "success":
            try:
                actual = DevicePosting.model_validate(result.get("data"), strict=True).model_dump()
                status = "valid"
            except ValidationError as validation_error:
                status, error = "invalid", str(validation_error)
    matches = {
        field: actual is not None and (
            set(actual[field]) == set(expected[field]) if field in LIST_FIELDS
            else actual[field] == expected[field]
        )
        for field in FIELDS
    }
    duplicates = {
        field: sorted(value for value, count in Counter(actual[field]).items() if count > 1)
        for field in LIST_FIELDS
    } if actual is not None else {}
    return {
        "document_id": document_id, "status": status, "error": error,
        "input_sha256": record["input_sha256"] if record else None,
        "expected": expected, "actual": actual, "field_matches": matches,
        "duplicate_list_values": {field: values for field, values in duplicates.items() if values},
    }


def list_metrics(documents: list[dict], field: str) -> dict:
    """Оцінює знайдені елементи одного спискового поля в усіх еталонних статтях.

    TP — правильно знайдені теги, FP — зайві теги, FN — пропущені теги.
    Спочатку додає ці кількості за всіма статтями, а потім рахує показники.
    Precision показує частку правильних серед знайдених тегів; recall —
    частку знайдених серед потрібних; F1 узгоджує ці два показники.
    Невдала або відсутня відповідь вважається порожнім списком, тому потрібні
    теги стають пропусками. Повтори тегів рахуються лише раз.
    Повертає кількості й показники; якщо ділити довелося б на нуль — None.
    """
    tp = fp = fn = 0
    for document in documents:
        expected = set(document["expected"][field])
        actual = set(document["actual"][field]) if document["actual"] is not None else set()
        tp += len(actual & expected)
        fp += len(actual - expected)
        fn += len(expected - actual)
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
    }


def evaluate_run(records: list[dict], golden: dict[str, dict]) -> dict:
    """Підсумовує якість одного запуску на всьому наборі еталонних статей.

    Знаходить відповіді за ID та порівнює їх з еталонами. Для кожного поля
    ділить кількість збігів на кількість усіх еталонів, включно з пропущеними
    й невдалими відповідями. Загальна accuracy — середнє восьми таких часток.
    Повертає ці оцінки, показники списків і розбіжності за кожною статтею.
    Статті поза golden не впливають на оцінки; їх кількість зазначається окремо.
    """
    if not golden:
        raise ValueError("Golden не може бути порожнім")
    indexed = index_records(records, "JSONL")
    configuration = run_configuration(records)
    documents = [score_document(key, value, indexed.get(key)) for key, value in golden.items()]
    count = len(documents)
    correct = {field: sum(document["field_matches"][field] for document in documents) for field in FIELDS}
    accuracy = {field: value / count for field, value in correct.items()}
    return {
        "configuration": configuration,
        "golden_documents": count,
        "present_golden_results": len(golden.keys() & indexed.keys()),
        "ignored_non_golden_results": len(indexed.keys() - golden.keys()),
        "document_status_counts": {status: sum(doc["status"] == status for doc in documents)
                                   for status in ("valid", "missing", "failed", "invalid")},
        "field_correct": correct, "field_accuracy": accuracy,
        "aggregate_accuracy": sum(accuracy.values()) / len(FIELDS),
        "list_metrics": {field: list_metrics(documents, field) for field in LIST_FIELDS},
        "documents": documents,
    }


def verify_same_inputs(runs: list[dict]) -> None:
    """Звіряє відбитки текстів, на яких отримано відповіді різних запусків.

    Для кожного спільного ID порівнює input_sha256 — контрольний відбиток
    фактичного тексту, переданого моделі. Різні відбитки зупиняють спільне
    оцінювання, адже умови експериментів відрізнялися. Відсутні відповіді
    пропускає; якщо суперечностей немає, завершується без результату.
    """
    inputs = {}
    for run in runs:
        for document in run["documents"]:
            digest = document["input_sha256"]
            if digest is None:
                continue
            document_id = document["document_id"]
            if document_id in inputs and inputs[document_id] != digest:
                raise ValueError(f"{document_id}: різні input_sha256; оцінюйте ці прогони окремо")
            inputs[document_id] = digest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Читає вибрані користувачем шляхи з команди запуску.

    Розпізнає файли результатів, шлях до golden і шлях нового звіту.
    Якщо argv не передано, читає аргументи з командного рядка.
    Повертає налаштування для main; самі файли ще не відкриває.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="JSONL; типово всі results/*.jsonl")
    parser.add_argument("--golden", type=Path, default=GOLDEN)
    parser.add_argument("--output", type=Path, help="Новий JSON-файл метрик і розбіжностей")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Керує повним оцінюванням: від вибору файлів до збереження звіту.

    Читає golden та вибрані JSONL; без списку файлів бере всі results/*.jsonl.
    Оцінює кожен запуск, звіряє входи й записує новий JSON із метриками,
    розбіжностями, умовами оцінювання та відбитками використаних файлів.
    Якщо хоча б один еталон не approved, позначає висновки як попередні.
    Виводить короткі оцінки й шлях звіту; наявний файл не перезаписує.
    Працює зі збереженими даними, без запитів до моделей.
    """
    args = parse_args(argv)
    files = args.files or sorted(RESULTS.glob("*.jsonl"))
    if not files:
        raise ValueError("Не знайдено JSONL для оцінювання")
    golden = load_golden(args.golden)
    runs = []
    for path in files:
        run = evaluate_run(load_run(path), golden)
        run.update(source_path=str(path.resolve()), source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        runs.append(run)
    verify_same_inputs(runs)
    timestamp = datetime.now(timezone.utc)
    report = {
        "evaluator_version": EVALUATOR_VERSION,
        "timestamp": timestamp.isoformat(),
        "golden_path": str(args.golden.resolve()),
        "golden_sha256": hashlib.sha256(args.golden.read_bytes()).hexdigest(),
        "provisional": any(row.get("annotation_status") != "approved" for row in golden.values()),
        "method": {
            "scalars": "exact", "lists": "exact-set; order and duplicates ignored",
            "normalization": "none", "aggregate": "macro mean of all 8 field accuracies",
            "denominator": "all golden documents; missing/failed/invalid score zero for all fields",
            "list_prf": "micro counts across golden; undefined ratios are null",
            "prediction": "final result after optional repair",
        },
        "runs": runs,
    }
    output = args.output or RESULTS / "evaluation" / f"golden_{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as destination:
        json.dump(report, destination, ensure_ascii=False, indent=2, allow_nan=False)
        destination.write("\n")
    if report["provisional"]:
        print("PROVISIONAL: не всі еталони мають статус approved")
    for run in runs:
        config = run["configuration"]
        print(f"{config['model']} | {config['prompt_version']} | "
              f"{json.dumps(config['sampling'], sort_keys=True)} | aggregate={run['aggregate_accuracy']:.4f}")
        print("  " + " | ".join(f"{field}={value:.3f}" for field, value in run["field_accuracy"].items()))
    print(f"Метрики й розбіжності: {output}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(f"Помилка оцінювання: {error}") from error
