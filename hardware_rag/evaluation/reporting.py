"""Рендеринг звіту тільки з збережених результатів, без нових LLM-викликів."""

from pathlib import Path
from ..artifacts import read_json


def render_report(run: dict) -> str:
    """Перетворює run artifact на Markdown із чесним статусом і помилками.

    Не вигадує точність, calibration чи production-рішення. За draft
    еталону явно пише provisional; первинна валідність і repairs подані
    окремо від фінальної якості відповідей.
    """
    lines = ["# HardwareResearch AI — ДЗ2", "", f"Run: `{run['run_id']}`", "",
             "Статус: **" + ("provisional — еталони/калібрування не підтверджені" if run.get("provisional") else "виміряний прогін") + "**", "",
             "## Метрики", "", "| Показник | Значення |", "| --- | --- |"]
    for key, value in run.get("metrics", {}).items():
        if not isinstance(value, (dict, list)):
            lines.append(f"| {key} | {value if value is not None else 'невідомо / incomplete'} |")
    lines += ["", "## Retrieval", "", "| Конфігурація | Recall@5 | MRR@5 | N |", "| --- | --- | --- | --- |"]
    for mode, metrics in run.get("retrieval", {}).items():
        lines.append(f"| {mode} | {metrics['recall_at_5']:.4f} | {metrics['mrr_at_5']:.4f} | {metrics['count']} |")
    records = run.get("records", [])
    if records:
        lines += ["", f"Первинно валідні: {sum(r['result']['first_attempt_valid'] for r in records)}/{len(records)}.",
                  f"Repair: {sum(any(a['kind'] == 'repair' for a in r['result']['attempts']) for r in records)}."]
        lines += _latencies(records)
    else:
        lines += ["", "Генерацію та якість відповідей у цьому прогоні не вимірювали."]
    cost = run.get("cost_usd")
    cost_text = str(cost) if cost is not None else ("невідомо" if records else "0 зовнішніх API USD; лише локальний retrieval")
    lines += ["", "## Витрати", "", f"Облік USD цього запуску: {cost_text}.",
              "Окремі components/usage наведено у JSON; одноразовий ingestion/index не включено до 1000 питань.",
              "Нуль зовнішніх витрат для локальних моделей не враховує обладнання й електрику.", "",
              "## Помилки для розбору", ""]
    if records:
        lines += ["| Компонент | Викликів | Input tokens | Output tokens | USD / 1000 питань |",
                  "| --- | --- | --- | --- | --- |"]
        for role, component in run.get("components", {}).items():
            usd = component["cost_usd"]
            per_1000 = f"{float(usd) / len(records) * 1000:.4f}" if usd is not None else "невідомо"
            lines.append(f"| {role} | {component['calls']} | {component['input_tokens']} | {component['output_tokens']} | {per_1000} |")
        lines += ["", "Екстраполяція з цього N, без індексації, за цінами без cache-знижки; не є рахунком провайдера.", ""]
    failures = [r for r in records if r["scores"].get("correct") is not True or r["scores"].get("faithful") is not True]
    for record in failures[:5]:
        lines += [f"### {record['case_id']}", f"- Очікуване: {record.get('reference', 'див. testset')}",
                  f"- Фактичне: {record['result']['answer']}",
                  "- Причина: потребує авторського аналізу доказів; автоматичний verdict збережений у JSON.", ""]
    if not records:
        lines.append("Помилки відповідей не вимірювали; retrieval rankings і причини провалу gate наведено окремо.")
    elif not failures:
        lines.append("У цьому прогоні таких випадків не зафіксовано; 3–5 помилок не вигадуються.")
    lines += ["", "## Quality gate", ""]
    lines += [f"- {failure}" for failure in run.get("gate_failures", [])] or ["Причин провалу не зафіксовано."]
    lines += ["", "## Межі перевірки", "", "- Human review і calibration підтверджуються тільки відповідними артефактами.",
              "- Справжній CI-run потребує user push/PR; локальні тести не підтверджують виконання GitHub Actions.",
              "- Авторське production-рішення й наступні покращення додаються після аналізу помилок."]
    return "\n".join(lines) + "\n"


def _latencies(records: list[dict]) -> list[str]:
    """Показує nearest-rank p50/p95 окремих виміряних етапів у секундах.

    Повний pipeline включає пошук/retry/repair, evaluation — також judge.
    Невиміряні значення не стають нулем: для кожного етапу видно N;
    це статистика наявних таймерів, а не виключення failed із quality.
    """
    import math
    lines = ["", "## Latency", "", "Nearest-rank; секунди. N — кількість фактично виміряних таймерів.", "",
             "| Етап | N | p50 | p95 |", "| --- | --- | --- | --- |"]
    for key in ("retrieval_seconds", "pipeline_seconds", "evaluation_seconds"):
        values = sorted(r[key] for r in records if r.get(key) is not None)
        if values:
            lines.append(f"| {key} | {len(values)} | {values[math.ceil(len(values)*.5)-1]:.4f} | {values[math.ceil(len(values)*.95)-1]:.4f} |")
        else:
            lines.append(f"| {key} | 0 | невідомо | невідомо |")
    return lines


def write_report(path: Path, run_path: Path) -> None:
    """Створює новий report-файл із зафіксованого run без перезапису.

    Наявний звіт користувача зберігається. Для нового вимірювання треба
    вказати інший шлях; кореневий REPORT ДЗ1 ця функція не обирає.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(render_report(read_json(run_path)))
