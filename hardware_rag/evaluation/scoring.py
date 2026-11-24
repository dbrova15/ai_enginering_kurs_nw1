"""Детерміновані оцінки й точні знаменники; жодної автоматичної правки еталонів."""

import re
import math
import unicodedata


def norm(text: str) -> str:
    """Уніфікує Unicode, регістр, пробіли й типографські мінуси для фактів.

    Не стирає одиниці, числа, десяткову крапку чи заперечення. Це
    зіставлення затверджених alternatives, не семантичний перекладач.
    """
    value = unicodedata.normalize("NFC", text).casefold().replace("−", "-").replace("–", "-")
    return " ".join(value.split())


def contains_fact(text: str, fact: str) -> bool:
    """Шукає факт із межами слів/чисел, не плутаючи 3 з 30 або ESP32 з S3.

    Символи fact екрануються як буквальні дані. Порожня альтернатива
    не зараховується як автоматично правильна відповідь.
    """
    expected = norm(fact)
    # Крапка наприкінці речення допустима; крапка перед цифрою є частиною числа.
    return bool(expected) and re.search(r"(?<![\w.+/-])" + re.escape(expected) + r"(?![\w+/-]|\.\d)", norm(text)) is not None


def retrieval_metrics(rankings: list[list[str]], relevant: list[list[str]], k: int = 5) -> dict:
    """Рахує macro recall@k і MRR@k на однаковій кількості answerable-кейсів.

    Recall — частка знайдених gold IDs, MRR — обернений ранг першого.
    Порожній gold, дублікати в ranking або неповний run відхиляються,
    щоб не зменшити знаменник після невдалого пошуку.
    """
    if not rankings or len(rankings) != len(relevant) or k < 1:
        raise ValueError("Неповний retrieval run")
    recalls, reciprocal = [], []
    for found, gold in zip(rankings, relevant):
        if not gold or len(set(found)) != len(found):
            raise ValueError("Порожній gold або дублікати rankings")
        top = found[:k]
        recalls.append(len(set(top).intersection(gold)) / len(set(gold)))
        reciprocal.append(next((1 / rank for rank, identifier in enumerate(top, 1) if identifier in gold), 0))
    return {"recall_at_5" if k == 5 else f"recall_at_{k}": sum(recalls) / len(recalls),
            "mrr_at_5" if k == 5 else f"mrr_at_{k}": sum(reciprocal) / len(reciprocal), "count": len(rankings)}


def score(result, case, *, judge_correct=None, faithful=None) -> dict:
    """Оцінює один фінальний результат, не виключаючи failed/false-abstain.

    Semantic correctness лишається unknown без calibrated judge. Citation
    score перевіряє релевантність gold, а формальний score — тільки
    належність реально наведених IDs фактичному контексту.
    """
    answer = result.answer if result.status == "success" else None
    found = answer is not None and answer.status != "not_found"
    cited = [i for claim in answer.claims for i in claim.chunk_ids] if answer else []
    formal = [i in result.selected_ids for i in cited]
    facts = None
    if case.answerable and case.scoring_mode == "deterministic":
        text = "\n".join(c.text for c in answer.claims) if found else ""
        facts = found and all(any(contains_fact(text, option) for option in group) for group in case.facts)
    correct = (facts if case.scoring_mode == "deterministic" else judge_correct) if case.answerable else None
    if case.answerable and not found:
        correct, faithful = False, False
    return {"correct": correct, "facts": facts,
            "cited": bool(found and set(cited).intersection(case.relevant)) if case.answerable else None,
            "faithful": faithful if case.answerable else None,
            "abstain": answer is not None and answer.status == "not_found" if not case.answerable else None,
            "false_abstain": not found if case.answerable else None,
            "formal_citations": formal, "failed": result.status != "success"}


def aggregate(scores: list[dict], cases: list) -> dict:
    """Зводить метрики з counts і unknown; не відкидає неповні оцінки.

    Застосовні unknown дають null метрику, а не середнє по вдалих cases.
    N/A визначається типом питання до перегляду результатів.
    """
    if not cases or len(scores) != len(cases):
        raise ValueError("Неповний answer run")
    output = {"count": len(cases), "failed": sum(s["failed"] for s in scores)}
    for key in ("correct", "cited", "faithful", "abstain", "false_abstain"):
        applicable = [s[key] for s, c in zip(scores, cases) if (not c.answerable if key == "abstain" else c.answerable)]
        output[key] = sum(applicable) / len(applicable) if applicable and None not in applicable else None
        output[key + "_count"] = len(applicable)
    formal = [v for s in scores for v in s["formal_citations"]]
    output["formal_citations"] = sum(formal) / len(formal) if formal else None
    output["formal_citations_count"] = len(formal)
    output["complete"] = all(output[key] is not None for key in ("correct", "cited", "faithful", "abstain", "formal_citations"))
    return output


def calibration(judged: list[bool], human: list[bool]) -> dict:
    """Порівнює judge з ручними labels і повертає agreement/FP/FN та counts.

    false_pass/false_fail визначені відносно всього N, не лише одного
    класу. Обидва класи потрібні для чесної перевірки судді.
    """
    if len(judged) < 10 or len(judged) != len(human) or set(human) != {True, False}:
        raise ValueError("Калібрування потребує ≥10 ручних оцінок обох класів")
    n = len(human)
    return {"count": n, "agreement": sum(a == b for a, b in zip(judged, human)) / n,
            "false_pass": sum(a and not b for a, b in zip(judged, human)) / n,
            "false_fail": sum(not a and b for a, b in zip(judged, human)) / n}


def gate(metrics: dict, thresholds: dict, *, reviewed: bool, calibrated: bool) -> list[str]:
    """Повертає причини провалу gate, включно з incomplete і human review.

    Невідомий/порожній показник не вважається проходженням; baseline
    не змінюється. Пороги задає користувач до вимірів, а не під результат.
    """
    failures = []
    if not reviewed:
        failures.append("testset_unreviewed")
    if not calibrated:
        failures.append("judge_uncalibrated")
    if not metrics.get("complete"):
        failures.append("eval_incomplete")
    for key, minimum in thresholds.items():
        value = metrics.get(key)
        if not isinstance(minimum, (int, float)) or not math.isfinite(minimum) or not 0 <= minimum <= 1:
            failures.append(f"invalid_threshold:{key}")
            continue
        if value is None or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= 1:
            failures.append(f"threshold:{key}")
    return failures
