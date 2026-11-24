"""Формування контексту з цілих чанків і перевіркою повного payload."""

from ..artifacts import canonical_json

# Резерв на службове message/schema представлення перевіреного профілю.
TOKEN_MARGIN = 256


def build_context(hits: list[dict], question: str, system: str, schema: dict, tokens, config) -> dict:
    """Вміщує цілі ranked чанки у context budget, не обрізаючи докази.

    Ураховує system, question, schema та output reserve до включення
    кожного наступного чанка. Повертає serialized data, selected map і
    skipped IDs; reference/labels не є аргументами цієї функції.
    """
    base = tokens.count(canonical_json({"system": system, "question": question, "schema": schema}))
    if base + config.output_tokens + TOKEN_MARGIN >= config.model_context_tokens:
        raise ValueError("Питання/інструкції не вміщаються в model context")
    selected, skipped, records = {}, [], []
    for hit in hits:
        chunk = hit["chunk"]
        if chunk.chunk_id in selected:
            continue
        item = {"chunk_id": chunk.chunk_id, "title": chunk.title, "section": chunk.section,
                "page_start": chunk.page_start, "page_end": chunk.page_end, "text": chunk.text,
                "versions": [{"version": s.document_version, "date": s.published_at,
                              "family": s.document_family} for s in chunk.aliases]}
        trial = canonical_json(records + [item])
        count = tokens.count(trial)
        if count > config.context_tokens or base + count + config.output_tokens + TOKEN_MARGIN > config.model_context_tokens:
            skipped.append(chunk.chunk_id)
        else:
            records.append(item)
            selected[chunk.chunk_id] = chunk
    return {"text": canonical_json(records), "selected": selected, "skipped": skipped}
