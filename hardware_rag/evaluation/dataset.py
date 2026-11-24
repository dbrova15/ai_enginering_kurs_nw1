"""Читання й lint тестсету до дорогих model calls."""

from collections import Counter
from pathlib import Path
from ..artifacts import canonical_json, read_json
from ..eval_cases import EvalCase
from ..retrieval.search import allowed


def load_cases(path: Path) -> tuple[dict, list[EvalCase]]:
    """Читає testset envelope та strict JSON-mode записи кейсів.

    Metadata містить dataset_id і статус перевірки. Порожній або
    пошкоджений файл не підміняється навчальним тестсетом.
    """
    data = read_json(path)
    return data, [EvalCase.model_validate_json(canonical_json(c)) for c in data["cases"]]


def lint(envelope: dict, cases: list, manifest: dict, chunks: list, blocks: list[dict],
         *, require_review: bool = True) -> list[str]:
    """Повертає всі проблеми completeness/provenance/покриття тестсету.

    require_review=False дозволяє лише попередні дослідження draft;
    він ніколи не робить dataset approved і не відкриває фінальний gate.
    Перевіряє proof spans, relevant IDs та однакові фільтри кейсу.
    """
    problems = []
    if len(cases) < 20:
        problems.append("testset: потрібно щонайменше 20 питань")
    if sum(c.retrieval_member for c in cases) != 15:
        problems.append("retrieval: потрібно рівно 15 answerable-кейсів")
    if envelope.get("dataset_id") != manifest["dataset_id"]:
        problems.append("testset: stale dataset_id")
    if require_review and envelope.get("review_status") != "approved":
        problems.append("testset: ручне затвердження відсутнє")
    ids = [c.case_id for c in cases]
    if len(set(ids)) != len(ids):
        problems.append("testset: duplicate case_id")
    tags = Counter(tag for c in cases for tag in set(c.tags))
    for tag in ("no_answer", "similar_model", "outdated_version"):
        if tags[tag] < 2:
            problems.append(f"coverage: {tag} < 2")
    if not {c.language for c in chunks}.issubset({c.language for c in cases}):
        problems.append("coverage: не всі мови корпусу мають питання")
    by_id = {c.chunk_id: c for c in chunks}
    by_block = {b["block_id"]: b for b in blocks}
    for case in cases:
        prefix = case.case_id + ": "
        if require_review and case.review_status != "approved":
            problems.append(prefix + "людина ще не перевірила кейс")
        relevant = [by_id[i] for i in case.relevant if i in by_id]
        if len(relevant) != len(case.relevant) or len(set(case.relevant)) != len(case.relevant):
            problems.append(prefix + "unknown/duplicate relevant IDs")
        if any(not allowed(c, case.filter_language, case.filter_format) for c in relevant):
            problems.append(prefix + "relevant суперечить фільтрам")
        valid_evidence = []
        for evidence in case.evidence:
            block = by_block.get(evidence.block_id)
            if block is None or not 0 <= evidence.start < evidence.end <= len(block["text"]):
                problems.append(prefix + "невалідний evidence span")
                continue
            valid_evidence.append(block["text"][evidence.start:evidence.end])
            if not any(block_id == evidence.block_id and start <= evidence.start and end >= evidence.end
                       for c in relevant for block_id, start, end in c.spans):
                problems.append(prefix + "evidence не міститься у relevant chunk")
        if case.scoring_mode == "deterministic":
            from .scoring import contains_fact
            evidence_text = "\n".join(valid_evidence)
            if any(not any(contains_fact(evidence_text, option) for option in group) for group in case.facts):
                problems.append(prefix + "literal facts відсутні в evidence")
        if "outdated_version" in case.tags:
            if not any(a.version_status == "known" and a.document_version for c in relevant for a in c.aliases):
                problems.append(prefix + "version trap потребує підтверджених versions")
    return problems
