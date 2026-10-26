"""Markdown-оформлення чернетки REPORT без вибору production-конфігурації."""

import hashlib
import html
import json
import os
from pathlib import Path
from urllib.parse import quote

from evaluator import FIELDS, LIST_FIELDS


def cell(value) -> str:
    """Екранує текст для таблиць: дані моделі не стають HTML або Markdown-командами."""
    if value is None:
        return "н/д"
    return html.escape(str(value)).replace("`", "&#96;").replace("|", "\\|").replace("\n", " ")


def table(headers: list[str], rows: list[list]) -> list[str]:
    """Перетворює підписи й рядки даних на звичайну Markdown-таблицю."""
    return ["| " + " | ".join(cell(value) for value in headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)]


def number(value, *, percent=False) -> str:
    """Показує частку як відсоток або число; невідоме значення — н/д."""
    if value is None:
        return "н/д"
    return f"{value:.2%}" if percent else f"{value:.6f}"


def link(label: str, target: Path, output: Path) -> str:
    """Будує посилання відносно чернетки, підтримуючи пробіли й українські назви."""
    try:
        relative = os.path.relpath(target.resolve(), output.parent)
    except ValueError:
        relative = str(target.resolve())
    return f"[{label}]({quote(relative.replace(chr(92), '/'), safe='/.:')})"


def label(configuration: dict) -> list:
    """Повертає три колонки, які однозначно описують модель, промпт і sampling."""
    return [configuration["model"], configuration["prompt_version"], json.dumps(configuration["sampling"], sort_keys=True)]


def comparison_tables(combined: list[dict]) -> list[str]:
    """Формує порівняння якості, валідності, latency, usage та API-витрат."""
    summary, fields, lists, usage = [], [], [], []
    for item in combined:
        metrics = item["metrics"]
        prefix = label(metrics["configuration"])
        validity, latency = metrics["validity"], metrics["latency"]["pipeline"]
        times = f"{number(latency['p50_seconds'])} / {number(latency['p95_seconds'])}"
        if not latency["complete"]:
            times += " *неповні дані"
        summary.append(prefix + [f"{metrics['document_observations']} / {item['golden_observations']}",
                                 number(item["aggregate_accuracy"], percent=True),
                                 f"{number(validity['first_attempt_valid_rate'], percent=True)} / {number(validity['final_valid_rate'], percent=True)}",
                                 f"{validity['repair_attempted_count']} ({number(validity['repair_attempted_rate'], percent=True)})",
                                 times, number(metrics["cost"]["estimated_api_usd_per_1000_documents"])])
        fields.append(prefix + [number(item["field_accuracy"][field], percent=True) for field in FIELDS])
        for field in LIST_FIELDS:
            values = item["list_metrics"][field]
            lists.append(prefix + [field, values["tp"], values["fp"], values["fn"],
                                   *(number(values[name], percent=True) for name in ("precision", "recall", "f1"))])
        first = metrics["latency"]["first_attempt"]
        usage.append(prefix + [number(first["p50_seconds"]), number(first["p95_seconds"]), first["complete"],
                               metrics["usage"]["input_tokens"]["total"], metrics["usage"]["output_tokens"]["total"]])
    base = ["Модель", "Промпт", "Sampling"]
    return ["## Порівняння конфігурацій", "",
            *table(base + ["N обробок / golden-порівнянь", "Aggregate accuracy", "Валідні до / після repair", "Repair", "Повний p50 / p95, с", "API USD / 1000"], summary), "",
            "Валідність і час рахуються за всіма записаними обробками, accuracy — лише за golden. Для повторних прогонів знаменник включає повторні спостереження. Н/д означає невідоме, не нуль.", "",
            "### Accuracy окремих полів", "", *table(base + list(FIELDS), fields), "",
            "### Списки: micro precision / recall / F1", "",
            *table(base + ["Поле", "TP", "FP", "FN", "Precision", "Recall", "F1"], lists), "",
            "### Перший виклик та usage", "",
            *table(base + ["Перший p50, с", "Перший p95, с", "Latency повна", "Input tokens", "Output tokens"], usage), ""]


def error_sections(examples: list[dict], output: Path) -> list[str]:
    """Описує перевірені розбіжності; причини та висновки залишає автору."""
    lines = ["## Реальні розбіжності з golden", "",
             "Автоматично підтверджено розбіжність із еталоном, а не причину її виникнення. Автор має звірити текст і пояснення; сам golden теж може містити помилку.", ""]
    if len(examples) < 3:
        lines.extend([f"Знайдено лише {len(examples)} різних статей із розбіжностями; додаткових прикладів не вигадано.", ""])
    for index, example in enumerate(examples, 1):
        document, field = example["document"], example["field"]
        config = example["configuration"]
        expected = document["expected"][field] if field else document["expected"]
        actual = document["actual"][field] if field and document["actual"] is not None else document["actual"]
        lines.extend([f"### {index}. {cell(document['document_id'])}: {cell(field or document['status'])}", "",
                      f"Конфігурація: {cell(config['model'])}, промпт {cell(config['prompt_version'])}, sampling {cell(json.dumps(config['sampling'], sort_keys=True))}.", "",
                      f"Джерело відповіді: {link('первинний JSONL', example['source'], output)}.", ""])
        text_path = Path(example["text_path"]) if example["text_path"] else None
        if text_path and text_path.is_file():
            if hashlib.sha256(text_path.read_bytes()).hexdigest() != example["text_sha256"]:
                raise ValueError(f"Текст статті змінився: {text_path}")
            lines.extend([f"Доказ для перевірки автором: {link('текст статті', text_path, output)}.", ""])
        else:
            lines.extend(["Текст статті недоступний за збереженим шляхом; автор має відновити його для перевірки причини.", ""])
        lines.extend(["Очікуване й фактичне значення:", "", "```json",
                      json.dumps({"expected": expected, "actual": actual}, ensure_ascii=False, indent=2), "```", "",
                      "**Причина:** [ЗАПОВНЮЄ АВТОР після читання статті; автоматично не встановлена].", "",
                      "**Висновок:** [ЗАПОВНЮЄ АВТОР: що показує приклад і як перевірити запропоноване пояснення].", ""])
    return lines


def render_report(context: dict) -> str:
    """Збирає чернетку зі звірених метрик; не затверджує причини чи production-вибір."""
    evaluation, metrics, output = context["evaluation"], context["metrics"], context["output_path"]
    provisional = evaluation["provisional"]
    lines = ["# HardwareResearch AI — порівняльний звіт (ЧЕРНЕТКА)", "",
             "Статус: потребує авторської перевірки причин помилок, production-вибору та умов його перегляду.", "",
             f"Згенеровано UTC: {context['timestamp']}", "",
             "## Дані й методика", "",
             f"Схема: v2. Golden: {len(context['golden'])} документів. Provisional: {str(provisional).lower()}.", "",
             f"Еталон: {link('golden', Path(evaluation['golden_path']), output)}; SHA-256 `{evaluation['golden_sha256']}`.", "",
             "Метрики evaluator й агрегатора повторно звірено з первинними JSONL та їхніми хешами. Конфігурації зіставлено за моделлю, версією/хешем промпту, sampling, схемою, підготовкою та точним набором джерел.", "",
             "Оцінюється фінальна відповідь після можливого repair. Скалярні поля порівнюються точно, списки — як множини без нормалізації; дублікати тегів не впливають на exact-set. Missing/failed/invalid дають нуль за всі вісім полів. Aggregate — середнє восьми field accuracy. Метрики списків — micro TP/FP/FN; невизначені частки — н/д.", ""]
    if provisional:
        lines.extend(["**Попередні оцінки:** не всі еталони затверджені людиною. Ця чернетка не змінює їхніх статусів.", ""])
    lines.extend(comparison_tables(context["combined"]))
    lines.extend(["## Припущення latency та вартості", "", *(f"- {cell(item)}" for item in metrics["assumptions"]), "",
                  "### Тарифні припущення", ""])
    pricing = {item["metrics"]["configuration"]["model"]: item["metrics"]["cost"]["pricing"] for item in context["combined"]}
    for model, tariff in pricing.items():
        lines.append(f"- {cell(model)}: {cell(json.dumps(tariff, ensure_ascii=False, sort_keys=True)) if tariff else 'тариф невідомий; вартість не оцінена' }.")
    lines.append("")
    lines.extend(error_sections(context["examples"], output))
    lines.extend(["## Вибір автора для production", "",
                  "[ЗАПОВНЮЄ АВТОР одним абзацом: модель, промпт і sampling; потрібна точність, допустимі затримка/вартість, вимоги локальності даних та обґрунтування компромісу з посиланням на таблиці.]", "",
                  "## Умови перегляду рішення", "",
                  "- [АВТОР: поріг прийнятної якості та спосіб перевірки на нових даних.]",
                  "- [АВТОР: умови зміни ціни, latency або доступності моделі.]",
                  "- [АВТОР: коли зміна корпусу, моделі чи промпту вимагає повторного порівняння.]", "",
                  "## Обмеження", "",
                  "Результати описують цю вибірку. Один прогін на конфігурацію не доводить статистичної переваги; cold start не відокремлений. Ціни є оцінками за snapshot-тарифами. Джерела з різними входами чи неповними метриками потребують окремого аналізу.", "",
                  "## Джерела звіту", "",
                  f"- {link('Evaluator JSON', context['evaluation_path'], output)}; SHA-256 `{context['evaluation_sha256']}`.",
                  f"- {link('Агрегатор JSON', context['metrics_path'], output)}; SHA-256 `{context['metrics_sha256']}`.", "",
                  "До публікації REPORT.md автор має заповнити всі позначені розділи та перевірити приклади. Генератор не робить нових модельних запитів і не оголошує чернетку завершеним звітом."])
    return "\n".join(lines) + "\n"
