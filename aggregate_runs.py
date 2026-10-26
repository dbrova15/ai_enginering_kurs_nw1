"""Офлайн-агрегація валідності, latency, usage та API-витрат із JSONL."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from evaluator import index_records, load_run, run_configuration
from main import RESULTS
from run_metrics import summarize_results

AGGREGATOR_VERSION = "run-metrics-v1"
ASSUMPTIONS = [
    "Одиниця обліку — записана обробка статті; невдалі обробки входять у знаменники й latency.",
    "Першу валідність беремо з first_attempt_valid; фінальний успіх повторно перевіряємо за Schema v2.",
    "Час у секундах; nearest rank: відсортоване значення з номером ceil(p*N). Неповні заміри позначені complete=false.",
    "first_attempt_seconds включає retry першого виклику; seconds також включає repair й валідацію, без читання TXT та запису JSONL.",
    "Cold start не позначений у журналах і може входити в latency; це не steady-state benchmark.",
    "Токени сумуються за журналами разом із repair. Невідомий usage не замінюється нулем; приховані SDK-retry не відновлюються.",
    "API-вартість — оцінка за повним input-тарифом без кеш-знижки, не рахунок провайдера.",
    "Провайдер у первинних JSONL не записаний: відповідність model ID тарифу/локальному запуску є явним припущенням MODEL_PRICING.",
    "Вартість/1000 — екстраполяція з усіх записаних обробок за незмінних довжин, якості та частоти помилок.",
    "Для локальної моделі нульові лише зовнішні API-витрати; обладнання та електроенергія не оцінені.",
    "Повторні файли однієї конфігурації об'єднуються як повторні спостереження; run_count й unique_documents показують повторення.",
    "Повністю відсутні в JSONL обробки невідомі: агрегатор не відновлює план експерименту чи перервані до запису запити.",
    "Accuracy на golden обчислюється окремо через evaluator.py; ці метрики охоплюють усі статті прогону.",
]


def aggregate_files(files: list[Path]) -> list[dict]:
    """Читає JSONL і об'єднує лише однакові конфігурації; файли не змінює.

    Відхиляє повторну передачу того самого файлу, дублікати ID всередині
    прогону та зміну тексту для одного ID. Зберігає джерела й їхні хеші.
    """
    groups, seen_files, inputs = {}, set(), {}
    for path in files:
        resolved = path.resolve()
        if resolved in seen_files:
            raise ValueError(f"Файл передано повторно: {path}")
        seen_files.add(resolved)
        records = load_run(path)
        index_records(records, str(path))
        configuration = run_configuration(records)
        key_configuration = dict(configuration)
        key_configuration["sampling"] = {
            field: float(value) if type(value) in (int, float) else value
            for field, value in configuration["sampling"].items()
        }
        key = json.dumps(key_configuration, sort_keys=True, allow_nan=False)
        group = groups.setdefault(key, {"configuration": configuration, "sources": [], "records": []})
        for record in records:
            fingerprint = (record.get("source_sha256"), record.get("input_sha256"))
            if any(not isinstance(value, str) or not value for value in fingerprint):
                raise ValueError(f"{path}: відсутні source/input-хеші")
            document_id = record["document_id"]
            if document_id in inputs and inputs[document_id] != fingerprint:
                raise ValueError(f"{document_id}: різні source/input-хеші; агрегуйте окремо")
            inputs[document_id] = fingerprint
        group["records"].extend(records)
        group["sources"].append({"path": str(resolved), "records": len(records),
                                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    summaries = []
    for key in sorted(groups):
        group = groups[key]
        metrics = summarize_results([row.get("result") for row in group["records"]], group["configuration"]["model"])
        metrics.update(configuration=group["configuration"], sources=group["sources"],
                       run_count=len(group["sources"]),
                       unique_documents=len({row["document_id"] for row in group["records"]}))
        summaries.append(metrics)
    return summaries


def format_number(value: float | None, digits: int = 3) -> str:
    """Показує число з потрібною точністю або н/д замість невідомого значення."""
    return f"{value:.{digits}f}" if value is not None else "н/д"


def markdown_table(groups: list[dict], phase: str) -> list[str]:
    """Створює таблицю повного часу або першої спроби; зірочка означає пропуски."""
    lines = [
        "| Модель | Промпт | Sampling | Файлів / обробок / унікальних ID | Валідні до / після | Repair | p50 / p95, с | Input / output tokens | API USD / 1000 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for group in groups:
        config, validity = group["configuration"], group["validity"]
        latency, usage = group["latency"][phase], group["usage"]
        times = f"{format_number(latency['p50_seconds'])} / {format_number(latency['p95_seconds'])}"
        if not latency["complete"]:
            times += " *"
        tokens = " / ".join(str(usage[field]["total"]) if usage[field]["total"] is not None else "н/д"
                            for field in ("input_tokens", "output_tokens"))
        values = [config["model"], config["prompt_version"], json.dumps(config["sampling"], sort_keys=True),
                  f"{group['run_count']} / {group['document_observations']} / {group['unique_documents']}",
                  f"{validity['first_attempt_valid_rate']:.1%} / {validity['final_valid_rate']:.1%}",
                  f"{validity['repair_attempted_count']} ({validity['repair_attempted_rate']:.1%})",
                  times, tokens, format_number(group["cost"]["estimated_api_usd_per_1000_documents"], 6)]
        lines.append("| " + " | ".join(str(value).replace("|", "\\|").replace("\n", " ") for value in values) + " |")
    return lines


def render_markdown(report: dict) -> str:
    """Формує читабельний звіт: дві таблиці, тарифи, джерела й усі припущення."""
    lines = ["# Агреговані метрики прогонів", "", f"UTC: {report['timestamp']}", "",
             "## Повна обробка: seconds", "", *markdown_table(report["groups"], "pipeline"), "",
             "## Перший виклик: first_attempt_seconds", "", *markdown_table(report["groups"], "first_attempt"), "",
             "Зірочка (*) означає, що час частини обробок невідомий: перцентилі стосуються лише відомих значень.", "",
             "## Припущення", "", *(f"- {item}" for item in report["assumptions"]), "",
             "## Тарифи", ""]
    models = {}
    for group in report["groups"]:
        models[group["configuration"]["model"]] = group["cost"]["pricing"]
    for model, pricing in models.items():
        if pricing is None:
            lines.append(f"- {model}: тариф невідомий, вартість не оцінена.")
        else:
            lines.append(f"- {model}: {pricing['kind']}; input/output USD за 1M: "
                         f"{pricing['input_per_million']} / {pricing['output_per_million']}; "
                         f"дата {pricing['checked_date']}; джерело: {pricing['source']}.")
    lines.extend(["", "## Джерела й конфігурації", ""])
    for group in report["groups"]:
        config = group["configuration"]
        lines.append(f"- {config['model']} / {config['prompt_version']}: prompt_sha256={config['prompt_sha256']}, "
                     f"preparation_version={config['preparation_version']}.")
        lines.extend(f"  - {Path(source['path']).name}: {source['records']} записів; SHA-256 {source['sha256']}."
                     for source in group["sources"])
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Читає шляхи JSONL та необов'язковий шлях нового JSON-звіту."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="Типово всі results/*.jsonl")
    parser.add_argument("--output", type=Path, help="Новий .json; поряд створюється однойменний .md")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Агрегує вибрані файли та записує нові JSON і Markdown без перезапису."""
    args = parse_args(argv)
    files = args.files or sorted(RESULTS.glob("*.jsonl"))
    if not files:
        raise ValueError("Не знайдено JSONL для агрегації")
    timestamp = datetime.now(timezone.utc)
    groups = aggregate_files(files)
    report = {"aggregator_version": AGGREGATOR_VERSION, "timestamp": timestamp.isoformat(),
              "assumptions": ASSUMPTIONS, "groups": groups}
    output = args.output or RESULTS / "metrics" / f"runs_{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    if output.suffix.lower() != ".json":
        raise ValueError("--output має вказувати файл .json")
    markdown = output.with_suffix(".md")
    if output.exists() or markdown.exists():
        raise FileExistsError("JSON або Markdown звіту вже існує; виберіть нове ім'я")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as json_file, markdown.open("x", encoding="utf-8") as md_file:
        json.dump(report, json_file, ensure_ascii=False, indent=2, allow_nan=False)
        json_file.write("\n")
        md_file.write(render_markdown(report))
    print(f"Конфігурацій: {len(groups)}; файлів: {len(files)}")
    print(f"JSON: {output}\nMarkdown: {markdown}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(f"Помилка агрегації: {error}") from error
