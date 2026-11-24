"""Операції CLI: композиція модулів без дублювання ingestion/retrieval правил."""

from pathlib import Path
from .artifacts import digest, read_json, write_json, text_digest
from .config import ROOT
from .ingestion.pipeline import current_dataset, load_dataset


def prepare(config, download: bool) -> dict:
    """Готує або перевіряє assets лише за явною CLI-командою bootstrap.

    download=True дозволяє публічні model/tokenizer files, але не API.
    Звичайна перевірка не виправляє cache мережевим отриманням файлів.
    """
    from .retrieval.assets import prepare_assets
    from .generation.tokenization import LlmTokens, prepare_encoding
    directory = config.path("assets")
    metadata = prepare_assets(directory, download=download)
    if download and not (directory / "llm-tokenizer.json").exists():
        prepare_encoding(directory)
    else:
        LlmTokens(directory, config.tokenizer_encoding)
    return {role: {"model": item["model"], "revision": item["revision"]} for role, item in metadata.items()}


def index(config) -> dict:
    """Індексує поточний завершений dataset із локальними embeddings.

    Дозвіл/наявність originals перевірені ingestion; тут додатково
    перевіряються assets і dataset hashes. Не перебудовує ДЗ1.
    """
    from .retrieval.tokenization import ModelTokens
    from .retrieval.embeddings import Embedder
    from .retrieval.index import build_index
    manifest, chunks = load_dataset(current_dataset(config, ROOT))
    tokens = ModelTokens(config.path("assets"))
    return build_index(manifest, chunks, Embedder(config.path("assets"), tokens), tokens, config, ROOT)


def ingest(config) -> dict:
    """Обробляє погоджені локальні originals у новий frozen dataset.

    Не отримує URLs і не змінює review status; returns manifest після
    count/format/hash перевірок. Помилки не знищують попередній current.
    """
    from .retrieval.tokenization import ModelTokens
    from .ingestion.pipeline import ingest as run_ingest
    manifest = run_ingest(config, ModelTokens(config.path("assets")), ROOT)
    return {key: value for key, value in manifest.items() if key != "fingerprint"}


def ask(config, question: str, language=None, document_format=None) -> dict:
    """Виконує одну відповідь за готовим індексом і зберігає її run record.

    Платний provider відкривається тільки для непорожніх hits і paid
    profile. Повертає Markdown та шлях запису; еталон не читається.
    """
    from .runtime import retrieval_runtime, approved_budget
    from .generation.client import LlmClient
    from .generation.tokenization import LlmTokens
    from .generation.pipeline import generate, render
    import uuid
    import time
    started = time.perf_counter()
    with retrieval_runtime(config, ROOT, rerank=config.retrieval == "hybrid+rerank") as (manifest, _, retriever):
        hits = retriever.search(question, language, document_format)
        retrieval_seconds = time.perf_counter() - started
        tokens = LlmTokens(config.path("assets"), config.tokenizer_encoding)
        budget = approved_budget(config) if hits else None
        client = LlmClient(config, tokens, budget) if hits else None
        system = config.path("generator_prompt").read_text(encoding="utf-8")
        result, context = generate(question, hits, system, client, tokens, config)
        identifier = "ask-" + uuid.uuid4().hex
        record = {"run_id": identifier, "question": question, "dataset_id": manifest["dataset_id"],
                  "index_id": read_json(config.path("indexes") / "current.json")["index_id"],
                  "chunks_sha256": manifest["chunks_sha256"], "config": config.model_dump(mode="json"),
                  "hits": [{"rank": rank, "chunk_id": hit["chunk"].chunk_id, "score": hit["score"]}
                           for rank, hit in enumerate(hits, 1)],
                  "filters": {"language": language, "format": document_format},
                  "config_sha256": digest(config.model_dump(mode="json")), "prompt_sha256": text_digest(system),
                  "prompt_version": config.path("generator_prompt").parent.name,
                  "retrieval_seconds": retrieval_seconds, "pipeline_seconds": time.perf_counter() - started,
                  "context": context["text"], "skipped": context["skipped"], "result": result.model_dump(mode="json"),
                  "cost_usd": str(budget.spent) if budget else None}
        path = config.path("runs") / identifier / "answer.json"
        write_json(path, record)
        if result.answer is None:
            raise ValueError("generation_failed: перевірте збережений run record")
        return {"answer": render(result.answer, context["selected"], document_format), "record": str(path)}


def compare_chunking(config, output: Path) -> dict:
    """Порівнює heading і fixed на двох HTML та одному PDF originals.

    Показує counts/median/max та приклади proof spans. Ручний QA
    залишається pending: автоматична статистика не оцінює візуальну
    правильність таблиць або вибір оптимальної стратегії.
    """
    from statistics import median
    from .ingestion.pipeline import source_records
    from .ingestion.html import extract_html
    from .ingestion.pdf import extract_pdf
    from .ingestion.normalize import normalize_blocks
    from .ingestion.chunking import CHUNKING_VERSION, make_chunks
    from .retrieval.tokenization import ModelTokens
    from .artifacts import within
    tokens = ModelTokens(config.path("assets"))
    sources = source_records(config.path("sources"))
    selected = [s for s in sources if s.format == "html"][:2] + [s for s in sources if s.format == "pdf"][:1]
    if len(selected) < 3:
        raise ValueError("Потрібні три документи обох форматів")
    rows = []
    for source in selected:
        path = within(ROOT, source.path)
        blocks = extract_html(path, source.selector) if source.format == "html" else extract_pdf(path)
        content_hash, blocks = normalize_blocks(blocks)
        for fixed in (False, True):
            chunks = make_chunks(blocks, [source], content_hash, tokens, config, fixed=fixed)
            counts = [tokens.count(tokens.passage(c.title, c.section, c.text)) for c in chunks]
            rows.append({"source_id": source.source_id, "strategy": "fixed" if fixed else "heading",
                         "count": len(chunks), "min": min(counts), "median": median(counts), "max": max(counts),
                         "examples": [{"section": c.section, "text": c.text[:400], "spans": c.spans} for c in chunks[:3]]})
    data = {"manual_review": "pending", "config_sha256": digest(config.model_dump(mode="json")),
            "chunking_version": CHUNKING_VERSION, "assets_sha256": digest(tokens.metadata),
            "sources": [{"source_id": s.source_id, "raw_sha256": s.raw_sha256} for s in selected],
            "comparison": rows}
    write_json(output, data)
    return data
