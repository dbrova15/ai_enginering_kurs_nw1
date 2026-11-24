"""RAG-координація й цитування; не читає reference, labels або golden."""

import time
import json
from pydantic import ValidationError
from ..answers import Answer, Result
from ..artifacts import canonical_json
from .context import build_context


def answer_schema() -> dict:
    """Створює strict JSON Schema тільки для payload відповіді моделі.

    Метадані запуску не входять у schema. extra=forbid успадковано
    від контракту, а додаткові семантичні інваріанти перевіряються локально.
    """
    return {"type": "json_schema", "json_schema": {"name": "rag_answer", "strict": True,
                                                       "schema": Answer.model_json_schema()}}


def validate_citations(answer: Answer, selected: dict) -> None:
    """Перевіряє, що всі цитати належать саме переданому контексту.

    Не доводить семантичну підтримку твердження: це відповідальність
    faithfulness eval. Невідома цитата породжує статичну безпечну помилку.
    """
    if any(identifier not in selected for claim in answer.claims for identifier in claim.chunk_ids):
        raise ValueError("citation_outside_context")


def generate(question: str, hits: list[dict], system: str, client, tokens, config) -> tuple[Result, dict]:
    """Генерує відповідь або одну repair-спробу за тим самим контекстом.

    Порожній контекст дає стандартний not_found без API. Refusal й
    transport failure є failed, а не чесною відмовою. Повертає Result
    і контекст для журналу/faithfulness, не змінюючи вихідні hits.
    """
    started = time.perf_counter()
    schema = answer_schema()
    context = build_context(hits, question, system, schema, tokens, config)
    selected = context["selected"]
    if not selected:
        answer = Answer(status="not_found", claims=[], limitations="")
        return Result(status="success", answer=answer, selected_ids=[], seconds=time.perf_counter() - started), context
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": canonical_json({"question": question,
                 "untrusted_sources": json.loads(context["text"])})}]
    before = len(client.attempts)
    first_valid = False
    error_text = None
    for repair in range(2):
        try:
            content = client.call(messages, schema, kind="repair" if repair else "primary")
        except ValueError as error:
            error_text = str(error)
            break
        try:
            answer = Answer.model_validate_json(content)
            validate_citations(answer, selected)
        except (ValidationError, ValueError) as error:
            if isinstance(error, ValidationError):
                details = [{"type": item["type"], "loc": item["loc"]}
                           for item in error.errors(include_input=False)]
                error_text = canonical_json(details)
            else:
                error_text = "citation_outside_context"
            client.attempts[-1].status = "invalid"
            client.attempts[-1].error = error_text
            messages += [{"role": "assistant", "content": content},
                         {"role": "user", "content": "Виправ лише формат JSON/IDs за тим самим контекстом. " + error_text}]
        else:
            first_valid = repair == 0
            client.attempts[-1].status = "valid"
            return Result(status="success", answer=answer, selected_ids=list(selected),
                          attempts=client.attempts[before:], seconds=time.perf_counter() - started,
                          first_attempt_valid=first_valid), context
    return Result(status="failed", answer=None, selected_ids=list(selected), attempts=client.attempts[before:],
                  error=error_text, seconds=time.perf_counter() - started, first_attempt_valid=first_valid), context


def render(answer: Answer, selected: dict, document_format: str | None = None) -> str:
    """Будує читабельну українську відповідь із source URLs із manifest.

    Модель визначає тільки chunk IDs, а не адреси. Для PDF додається
    page fragment. not_found завжди є стандартною фразою без довільного
    тексту LLM; partial явно показує обмеження підтвердженої відповіді.
    """
    if answer.status == "not_found":
        return "У документах недостатньо даних для відповіді."
    validate_citations(answer, selected)
    lines = []
    for claim in answer.claims:
        citations = []
        for identifier in claim.chunk_ids:
            chunk = selected[identifier]
            source = chunk.source_for(document_format)
            url = source.url or source.path
            if source.format == "pdf" and chunk.page_start:
                url = url.split("#")[0] + f"#page={chunk.page_start}"
            label = f"{source.title}: {chunk.section}".replace("[", "(").replace("]", ")")
            citations.append(f"[{label}]({url})")
        lines.append(claim.text + " " + "; ".join(citations))
    if answer.limitations:
        lines.append("Обмеження: " + answer.limitations)
    return "\n\n".join(lines)
