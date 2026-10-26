"""Чисті розрахунки метрик обробки документів без мережі та запису файлів."""

import math

from main import DevicePosting

# Зафіксований тариф експерименту; він не оновлюється автоматично.
MODEL_PRICING = {
    "gpt-4o-mini": {
        "assumed_provider": "openai", "kind": "external_api", "currency": "USD",
        "checked_date": "2026-10-26",
        "source": "https://developers.openai.com/api/docs/models/gpt-4o-mini",
        "input_per_million": 0.15, "output_per_million": 0.60,
    },
    "llama3.2:3b": {
        "assumed_provider": "ollama", "kind": "local", "currency": "USD",
        "checked_date": "2026-10-26",
        "source": "results/sampling_comparison_20261026.md",
        "input_per_million": 0.0, "output_per_million": 0.0,
    },
}


def known_values(results: list[dict], field: str, *, integer: bool = False) -> list:
    """Збирає відомі числові значення. Пропуски лишаються невідомими, не нулями.

    Від'ємні числа, нескінченність, bool і неправильні типи означають помилку
    в журналі. Для токенів дозволяються лише невід'ємні цілі числа.
    """
    values = []
    for result in results:
        value = result.get(field)
        if value is None:
            continue
        valid_type = type(value) is int if integer else type(value) in (int, float)
        if not valid_type or not math.isfinite(value) or value < 0:
            raise ValueError(f"Некоректне значення {field}: {value!r}")
        values.append(value)
    return values


def latency_summary(results: list[dict], field: str) -> dict:
    """Сортує час усіх відповідей, включно з невдалими, та знаходить p50/p95.

    Метод nearest rank бере елемент ceil(p*N): для 30 значень це 15-й і 29-й.
    Якщо частина часу невідома, показники рахуються лише за відомими значеннями
    й позначаються неповними. Якщо відомих значень немає, показники — None.
    """
    values = sorted(known_values(results, field))
    return {
        "samples": len(values), "missing": len(results) - len(values),
        "complete": len(values) == len(results),
        "p50_seconds": values[math.ceil(0.50 * len(values)) - 1] if values else None,
        "p95_seconds": values[math.ceil(0.95 * len(values)) - 1] if values else None,
    }


def token_summary(results: list[dict], field: str) -> dict:
    """Підсумовує токени. За наявності пропусків загальний total невідомий.

    Суму відомої частини зберігає окремо, щоб не видати її за повний usage.
    """
    values = known_values(results, field, integer=True)
    return {
        "total": sum(values) if len(values) == len(results) else None,
        "known_total": sum(values), "missing_documents": len(results) - len(values),
    }


def cost_summary(model: str, count: int, input_usage: dict, output_usage: dict) -> dict:
    """Оцінює API-вартість за токенами та зафіксованим тарифом моделі.

    Масштабує витрати до 1000 обробок за припущенням такої самої вибірки.
    Невідома модель чи неповний usage не дають повної оцінки. Для явно
    локальної моделі зовнішня API-вартість — нуль незалежно від usage;
    це не включає обладнання й електроенергію. Cached input не здешевлюється.
    """
    pricing = MODEL_PRICING.get(model)
    cost = {"pricing": pricing, "complete": False, "estimated_api_usd": None,
            "estimated_api_usd_per_1000_documents": None, "known_usage_api_usd": None}
    if pricing is None:
        cost["reason"] = "Для model ID немає зафіксованого тарифу"
        return cost
    known_cost = (input_usage["known_total"] * pricing["input_per_million"]
                  + output_usage["known_total"] * pricing["output_per_million"]) / 1_000_000
    complete = input_usage["total"] is not None and output_usage["total"] is not None
    if pricing["kind"] == "local":
        complete, known_cost = True, 0.0
    cost.update(complete=complete, known_usage_api_usd=known_cost)
    if complete:
        cost.update(estimated_api_usd=known_cost,
                    estimated_api_usd_per_1000_documents=known_cost / count * 1000)
    else:
        cost["reason"] = "Usage частини обробок невідомий; відома сума не є повною вартістю"
    return cost


def summarize_results(results: list[dict], model: str) -> dict:
    """Підсумовує обробки однієї конфігурації, не використовуючи golden.

    Валідність до repair бере з журналу; фінально успішні дані повторно
    перевіряє за схемою. У знаменнику залишаються всі записані обробки.
    Суперечливі прапорці зупиняють розрахунок. Повертає валідність, repair,
    два набори latency, usage та оцінку API-витрат.
    """
    if not results:
        raise ValueError("Немає обробок для агрегації")
    first_valid = final_valid = repairs = repaired_valid = 0
    for result in results:
        if not isinstance(result, dict):
            raise ValueError("result має бути об'єктом")
        if any(type(result.get(field)) is not bool for field in ("ok", "first_attempt_valid", "repair_attempted")):
            raise ValueError("Відсутні або некоректні прапорці валідності/repair")
        if result["ok"] != (result.get("status") == "success"):
            raise ValueError("Прапорець ok суперечить status")
        if result["first_attempt_valid"] and (not result["ok"] or result["repair_attempted"]):
            raise ValueError("Першу валідну відповідь помилково позначено failed або repair")
        if result["ok"] and not (result["first_attempt_valid"] or result["repair_attempted"]):
            raise ValueError("Успіх не пояснений первинною відповіддю або repair")
        if result["ok"]:
            DevicePosting.model_validate(result.get("data"), strict=True)
        first_valid += result["first_attempt_valid"]
        final_valid += result["ok"]
        repairs += result["repair_attempted"]
        repaired_valid += result["repair_attempted"] and result["ok"]
    count = len(results)
    inputs, outputs = token_summary(results, "input_tokens"), token_summary(results, "output_tokens")
    return {
        "document_observations": count,
        "validity": {
            "first_attempt_valid_count": first_valid, "first_attempt_valid_rate": first_valid / count,
            "final_valid_count": final_valid, "final_valid_rate": final_valid / count,
            "failed_count": count - final_valid,
            "repair_attempted_count": repairs, "repair_attempted_rate": repairs / count,
            "repaired_valid_count": repaired_valid,
            "repair_success_rate": repaired_valid / repairs if repairs else None,
        },
        "latency": {"first_attempt": latency_summary(results, "first_attempt_seconds"),
                    "pipeline": latency_summary(results, "seconds")},
        "usage": {"input_tokens": inputs, "output_tokens": outputs},
        "cost": cost_summary(model, count, inputs, outputs),
    }
