"""Генерує чернетку REPORT із явно вибраних офлайн-звітів, без викликів моделей."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from aggregate_runs import AGGREGATOR_VERSION, aggregate_files
from evaluator import EVALUATOR_VERSION, FIELDS, LIST_FIELDS, evaluate_run, list_metrics, load_golden, load_run, verify_same_inputs
from main import ROOT
from report_rendering import render_report


def digest(path: Path) -> str:
    """Обчислює контрольний відбиток файлу для звірки з джерелом звіту."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def configuration_key(configuration: dict) -> str:
    """Створює ключ усіх умов запуску; числа 0 та 0.0 в sampling рівнозначні."""
    normalized = dict(configuration)
    normalized["sampling"] = {
        field: float(value) if type(value) in (int, float) else value
        for field, value in configuration["sampling"].items()
    }
    return json.dumps(normalized, sort_keys=True, allow_nan=False)


def validate_evaluation(report: dict) -> tuple[dict, dict, dict]:
    """Звіряє golden та кожен evaluator-запис із незміненими первинними JSONL.

    Повторно обчислює оцінки офлайн: застарілі хеші або змінені метрики
    зупиняють генерацію, а не переносяться до чернетки непомітно.
    """
    if report.get("evaluator_version") != EVALUATOR_VERSION:
        raise ValueError("Непідтримувана версія evaluator-звіту")
    golden_path = Path(report["golden_path"])
    if digest(golden_path) != report["golden_sha256"]:
        raise ValueError("Golden змінився після оцінювання; повторіть evaluator")
    golden = load_golden(golden_path)
    provisional = any(row.get("annotation_status") != "approved" for row in golden.values())
    if report.get("provisional") is not provisional:
        raise ValueError("Статус provisional не відповідає golden")
    indexed, records = {}, {}
    if not report.get("runs"):
        raise ValueError("Evaluator-звіт не містить прогонів")
    for run in report["runs"]:
        path = Path(run["source_path"]).resolve()
        if path in indexed:
            raise ValueError(f"Дубльований прогін evaluator: {path}")
        if digest(path) != run["source_sha256"]:
            raise ValueError(f"JSONL змінився після оцінювання: {path}")
        rows = load_run(path)
        verified = evaluate_run(rows, golden)
        if any(run.get(field) != value for field, value in verified.items()):
            raise ValueError(f"Оцінки не відповідають первинним даним: {path}")
        indexed[path], records[path] = run, rows
    verify_same_inputs(list(indexed.values()))
    return golden, indexed, records


def match_reports(evaluation: dict, metrics: dict) -> tuple[list[dict], dict, dict]:
    """Поєднує лише ті метрики, що мають ті самі конфігурації й джерела.

    Повторні прогони однієї конфігурації підтримуються: точність обчислюється
    за всіма їхніми golden-порівняннями, а не береться з першого файлу.
    """
    golden, quality, records = validate_evaluation(evaluation)
    if metrics.get("aggregator_version") != AGGREGATOR_VERSION or not metrics.get("groups"):
        raise ValueError("Непідтримуваний або порожній звіт агрегатора")
    source_paths = [Path(source["path"]).resolve() for group in metrics["groups"] for source in group["sources"]]
    if set(source_paths) != set(quality):
        raise ValueError("Evaluator і агрегатор охоплюють різні JSONL; виберіть узгоджені звіти")
    verified_groups = {configuration_key(group["configuration"]): group for group in aggregate_files(source_paths)}
    if len(verified_groups) != len(metrics["groups"]):
        raise ValueError("У звіті агрегатора дубльовані або змішані групи")
    combined, seen = [], set()
    for group in metrics["groups"]:
        key = configuration_key(group["configuration"])
        if key in seen or group != verified_groups.get(key):
            raise ValueError("Метрики/тарифи не відповідають джерелам або чинній версії агрегатора; повторіть агрегацію")
        seen.add(key)
        runs = [quality[Path(source["path"]).resolve()] for source in group["sources"]]
        if any(configuration_key(run["configuration"]) != key for run in runs):
            raise ValueError("Конфігурації evaluator й агрегатора не збігаються")
        documents = [document for run in runs for document in run["documents"]]
        count = len(documents)
        accuracy = {field: sum(doc["field_matches"][field] for doc in documents) / count for field in FIELDS}
        combined.append({"metrics": group, "golden_observations": count,
                         "field_accuracy": accuracy, "aggregate_accuracy": sum(accuracy.values()) / len(FIELDS),
                         "list_metrics": {field: list_metrics(documents, field) for field in LIST_FIELDS}})
    combined.sort(key=lambda item: (item["metrics"]["configuration"]["model"], item["metrics"]["configuration"]["prompt_version"],
                                    json.dumps(item["metrics"]["configuration"]["sampling"], sort_keys=True)))
    return combined, golden, records


def select_examples(evaluation: dict, records: dict, limit: int) -> list[dict]:
    """Добирає різні типи справжніх розбіжностей, по можливості з різних статей.

    Не визначає психологічну чи технічну причину помилки моделі: для цього
    автор має прочитати статтю. Якщо розбіжностей мало, не вигадує додаткових.
    """
    priority = ("primary_topic", "mentioned_interfaces", "mentioned_platforms",
                "mentions_sensor", "mentions_display", "mentions_battery", "mentions_motor", "language")
    candidates = []
    for run in evaluation["runs"]:
        source = Path(run["source_path"]).resolve()
        indexed = {row["document_id"]: row for row in records[source]}
        for document in run["documents"]:
            fields = [field for field in priority if not document["field_matches"][field]]
            if document["status"] != "valid":
                fields = [None]
            for field in fields:
                kind = "mentions_boolean" if field and field.startswith("mentions_") else field or document["status"]
                row = indexed.get(document["document_id"], {})
                candidates.append({"document": document, "field": field, "kind": kind,
                                   "configuration": run["configuration"], "source": source,
                                   "text_path": row.get("source_path"), "text_sha256": row.get("source_sha256")})
    selected, used_ids, used_kinds = [], set(), set()
    for diverse in (True, False):
        for candidate in candidates:
            document_id = candidate["document"]["document_id"]
            if document_id in used_ids or (diverse and candidate["kind"] in used_kinds):
                continue
            selected.append(candidate)
            used_ids.add(document_id)
            used_kinds.add(candidate["kind"])
            if len(selected) == limit:
                return selected
    return selected


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Вимагає явних шляхів до двох звітів; назву чернетки можна змінити."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation", type=Path, required=True, help="JSON evaluator")
    parser.add_argument("--metrics", type=Path, required=True, help="JSON aggregate_runs")
    parser.add_argument("--output", type=Path, default=ROOT / "REPORT.draft.md")
    parser.add_argument("--examples", type=int, choices=(3, 4, 5), default=5)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Перевіряє дані та створює нову чернетку без мережі й перезапису файлів."""
    args = parse_args(argv)
    if args.output.exists():
        raise FileExistsError(f"Чернетка вже існує: {args.output}")
    evaluation = json.loads(args.evaluation.read_text(encoding="utf-8"))
    metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
    combined, golden, records = match_reports(evaluation, metrics)
    examples = select_examples(evaluation, records, args.examples)
    context = {"timestamp": datetime.now(timezone.utc).isoformat(), "evaluation": evaluation,
               "metrics": metrics, "combined": combined, "golden": golden, "examples": examples,
               "evaluation_path": args.evaluation.resolve(), "metrics_path": args.metrics.resolve(),
               "evaluation_sha256": digest(args.evaluation), "metrics_sha256": digest(args.metrics),
               "output_path": args.output.resolve()}
    draft = render_report(context)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as destination:
        destination.write(draft)
    print(f"Чернетка: {args.output}; конфігурацій: {len(combined)}; прикладів: {len(examples)}")
    print("Причини помилок, production-вибір та умови перегляду має заповнити автор.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise SystemExit(f"Помилка генерації чернетки: {error}") from error
