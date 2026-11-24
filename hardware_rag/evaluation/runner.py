"""Відтворювані retrieval/answer прогони та lineage, без переписування baseline."""

import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
from ..artifacts import canonical_json, digest, read_json, write_json, text_digest
from ..answers import Result
from ..generation.pipeline import generate
from .scoring import aggregate, gate, retrieval_metrics, score


def run_retrieval(retriever, cases: list) -> dict:
    """Порівнює 15 retrieval-кейсів у трьох режимах на одних фільтрах.

    Зберігає точні rankings і метрики за мовами, не лише aggregate.
    Відсутні результати рахуються як порожній top-k, не вилучають кейс.
    """
    subset = [c for c in cases if c.retrieval_member]
    if len(subset) != 15:
        raise ValueError("Потрібно рівно 15 retrieval-кейсів")
    output = {}
    for mode in ("vector", "hybrid", "hybrid+rerank"):
        rankings = [[h["chunk"].chunk_id for h in retriever.search(c.question, c.filter_language, c.filter_format, mode)] for c in subset]
        metrics = retrieval_metrics(rankings, [c.relevant for c in subset])
        metrics["rankings"] = dict(zip([c.case_id for c in subset], rankings))
        metrics["by_language"] = {}
        for language in sorted({c.language for c in subset}):
            pairs = [(ranking, c.relevant) for ranking, c in zip(rankings, subset) if c.language == language]
            metrics["by_language"][language] = retrieval_metrics([p[0] for p in pairs], [p[1] for p in pairs])
        output[mode] = metrics
    return output


def run_answers(retriever, cases: list, system: str, client, tokens, config, judge) -> tuple[list, dict]:
    """Генерує кожний кейс один раз і відділяє judge failures від результату бота.

    Зберігає contexts, reference тільки в evaluation artifact, а також
    source/hit IDs і окремі attempts судді. Після budget failure наступні
    запити блокуються Budget; run не видається за complete.
    """
    records, scores = [], []
    for case in cases:
        result = None
        started = time.perf_counter()
        retrieval_seconds, pipeline_seconds = None, None
        judge_before = len(judge.client.attempts)
        judge_correct, faithful, judged = None, None, {}
        context = {"selected": {}, "text": "[]", "skipped": []}
        hits = []
        try:
            hits = retriever.search(case.question, case.filter_language, case.filter_format)
            retrieval_seconds = time.perf_counter() - started
            result, context = generate(case.question, hits, system, client, tokens, config)
            pipeline_seconds = time.perf_counter() - started
            if result.answer is not None:
                if case.answerable and case.scoring_mode == "judge":
                    judge_correct, judged["correct_reason"] = judge.correct(case, result.answer)
                faithful, judged["claims"] = judge.faithful(result.answer, context["selected"])
        except Exception as error:
            # Provider bodies/keys не потрапляють у result; справжній тип потрібен для audit.
            judged["error"] = type(error).__name__
            if result is None:
                result = Result(status="failed", answer=None, selected_ids=[], error=type(error).__name__)
        item = score(result, case, judge_correct=judge_correct, faithful=faithful)
        records.append({"case_id": case.case_id, "reference": case.reference, "question": case.question,
                        "filters": {"language": case.filter_language, "format": case.filter_format},
                        "hits": [{"chunk_id": h["chunk"].chunk_id, "score": h["score"]} for h in hits],
                        "context": context["text"], "selected": list(context["selected"]),
                        "skipped": context["skipped"], "result": result.model_dump(mode="json"),
                        "scores": item, "judge": judged, "requested_model": getattr(client, "model", None),
                        "retrieval_seconds": retrieval_seconds, "pipeline_seconds": pipeline_seconds,
                        "evaluation_seconds": time.perf_counter() - started,
                        "provider": getattr(client, "provider", None),
                        "judge_attempts": [a.model_dump(mode="json") for a in judge.client.attempts[judge_before:]]})
        scores.append(item)
    return records, aggregate(scores, cases)


def save_run(config, root: Path, manifest: dict, envelope: dict, *, records=None,
             retrieval=None, metrics=None, budget=None, judge=None, calibration_data=None) -> dict:
    """Публікує новий immutable run з усіма hashes і результатом gate.

    Draft/uncalibrated метрики зберігаються як provisional; не створюють
    approved baseline. Кошти з невідомим usage залишаються оцінкою резерву.
    """
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    threshold_data = read_json(config.path("thresholds", root))
    reviewed = envelope.get("review_status") == "approved" and all(c.get("review_status") == "approved" for c in envelope["cases"])
    quality = dict(metrics or {})
    retrieval = retrieval or {}
    if config.retrieval in retrieval:
        quality["recall_at_5"] = retrieval[config.retrieval]["recall_at_5"]
    calibrated = bool(calibration_data and calibration_data.get("review_status") == "approved"
                      and judge and calibration_data.get("judge_identity") == judge.identity)
    if calibrated:
        actual_models = {a.actual_model for a in judge.client.attempts if a.actual_model}
        calibrated = bool(actual_models and actual_models == set(calibration_data.get("actual_models", [])))
    agreements = [v["agreement"] for v in (calibration_data or {}).get("metrics", {}).values()]
    quality["agreement"] = min(agreements) if calibrated and len(agreements) == 2 else None
    failures = gate(quality, threshold_data["metrics"], reviewed=reviewed, calibrated=calibrated)
    components = {}
    for role, attempts in (("generator", [a for r in records or [] for a in r["result"]["attempts"]]),
                           ("judge", [a for r in records or [] for a in r["judge_attempts"]])):
        unknown = any(a["input_tokens"] is None or a["output_tokens"] is None for a in attempts)
        input_tokens = sum(a["input_tokens"] or 0 for a in attempts)
        output_tokens = sum(a["output_tokens"] or 0 for a in attempts)
        amount = str(budget.price(input_tokens, output_tokens)) if budget and not unknown else None
        components[role] = {"calls": len(attempts), "input_tokens": None if unknown else input_tokens,
                            "output_tokens": None if unknown else output_tokens, "cost_usd": amount}
    data = {"run_id": run_id, "schema_version": "rag-eval-1", "dataset_id": manifest["dataset_id"],
            "chunks_sha256": manifest["chunks_sha256"], "config_sha256": digest(config.model_dump(mode="json")),
            "testset_sha256": digest(envelope), "prompt_sha256": text_digest(config.path("generator_prompt", root).read_text(encoding="utf-8")),
            "prompt_version": config.path("generator_prompt", root).parent.name,
            "judge_identity": judge.identity if judge else None, "provisional": not reviewed or not calibrated,
            "retrieval": retrieval, "records": records or [], "metrics": quality, "gate_failures": failures,
            "index_id": read_json(config.path("indexes", root) / "current.json")["index_id"],
            "config": config.model_dump(mode="json"), "components": components,
            "cost_usd": str(budget.spent) if budget else None,
            "usage_unknown_calls": budget.unknown_calls if budget else 0}
    directory = config.path("runs", root) / run_id
    write_json(directory / "run.json", data)
    with (directory / "report.md").open("x", encoding="utf-8") as stream:
        from .reporting import render_report
        stream.write(render_report(data))
    return data
