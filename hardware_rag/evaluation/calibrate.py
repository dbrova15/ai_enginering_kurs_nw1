"""Калібрування judge тільки на реальних відповідях із ручними labels."""

from pathlib import Path
from ..answers import Result
from ..artifacts import canonical_json, digest, read_json, write_json
from ..eval_cases import HumanLabel
from .scoring import calibration


def calibrate_run(run: dict, cases: list, chunks: list, labels_path: Path, judge, output: Path) -> dict:
    """Зіставляє ≥10 approved людських оцінок із повторними judge verdicts.

    Перед API перевіряє hashes відповідей/контексту та обидва класи
    ручних correct/faithful. Невідповідність блокує калібрування, а не
    призводить до автоматичного виправлення людини чи baseline.
    """
    labels = [HumanLabel.model_validate(item) for item in read_json(labels_path)["labels"]]
    if len(labels) < 10 or any(label.review_status != "approved" for label in labels):
        raise ValueError("Потрібно ≥10 реально перевірених людиною labels")
    by_case = {c.case_id: c for c in cases}
    by_chunk = {c.chunk_id: c for c in chunks}
    records = {r["case_id"]: r for r in run["records"]}
    if len({label.label_id for label in labels}) != len(labels):
        raise ValueError("Повторені label IDs")
    if len({label.case_id for label in labels}) != len(labels):
        raise ValueError("Для калібрування потрібні різні реальні відповіді, не повторні labels одного кейсу")
    for label in labels:
        record = records[label.case_id]
        if label.answer_sha256 != digest(record["result"]["answer"]) or label.context_sha256 != digest(record["context"]):
            raise ValueError("Label не відповідає реальній відповіді/контексту")
    if set(label.correct for label in labels) != {True, False}:
        raise ValueError("Для correctness потрібні ручні позитивні й негативні приклади")
    faithful_labels = [label for label in labels if label.faithful is not None]
    if len(faithful_labels) < 10 or {label.faithful for label in faithful_labels} != {True, False}:
        raise ValueError("Для faithfulness потрібні ≥10 ручних оцінок обох класів")
    predictions = []
    for label in labels:
        record = records[label.case_id]
        result = Result.model_validate_json(canonical_json(record["result"]))
        if result.answer is None:
            raise ValueError("Label має посилатися на змістовну відповідь моделі")
        selected = {identifier: by_chunk[identifier] for identifier in result.selected_ids}
        correct, reason = judge.correct(by_case[label.case_id], result.answer)
        faithful, details = judge.faithful(result.answer, selected)
        predictions.append({"label_id": label.label_id, "correct": correct, "faithful": faithful,
                            "reason": reason, "claims": details})
    metrics = {"correct": calibration([p["correct"] for p in predictions], [label.correct for label in labels]),
               "faithful": calibration([p["faithful"] for p, label in zip(predictions, labels) if label.faithful is not None],
                                        [label.faithful for label in faithful_labels])}
    data = {"review_status": "approved", "judge_identity": judge.identity, "run_id": run["run_id"],
            "labels_sha256": digest([label.model_dump(mode="json") for label in labels]),
            "metrics": metrics, "predictions": predictions,
            "actual_models": sorted({a.actual_model for a in judge.client.attempts if a.actual_model})}
    write_json(output, data)
    return data
