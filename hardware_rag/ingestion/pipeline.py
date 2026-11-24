"""Координація ingestion: approved originals → immutable dataset і manifest."""

import uuid
from pathlib import Path
from ..artifacts import digest, file_digest, read_json, within, write_json
from ..documents import Block, Chunk, Source
from .html import extract_html
from .pdf import extract_pdf
from .normalize import NORMALIZATION_VERSION, normalize_blocks
from .chunking import CHUNKING_VERSION, make_chunks

# Версія extraction: очевидні Arduino/C рядки у HTML <p> зберігаються як
# code, щоб prose cleanup не змінював string literals. Попередні PDF fixes
# лишаються; зміна гарантує нові dataset/index fingerprints.
EXTRACTION_VERSION = "rag-extract-6"
# Версія серіалізації відрізняє нові LF-артефакти від історичних CRLF-хешів.
ARTIFACT_SERIALIZATION = "utf8-lf"


def source_records(path: Path) -> list[Source]:
    """Читає source registry й перевіряє IDs та явне людське погодження.

    Повертає records тільки якщо всі approved, інакше блокує ingestion
    до обробки originals. Агент не змінює draft на approved автоматично.
    """
    envelope = read_json(path)
    if envelope.get("review_status") != "approved":
        raise ValueError("sources_unreviewed: реєстр не погоджений людиною")
    sources = [Source.model_validate(item) for item in envelope["sources"]]
    if not sources or len({s.source_id for s in sources}) != len(sources):
        raise ValueError("Реєстр порожній або source_id повторюються")
    if any(s.review_status != "approved" for s in sources):
        raise ValueError("sources_unreviewed: потрібне погодження реєстру людиною")
    return sorted(sources, key=lambda s: s.source_id)


def ingest(config, tokens, root: Path) -> dict:
    """Обробляє джерела з конфігурації в межах root і повертає manifest.

    Витягує й дедуплікує документи, нарізає їх за допомогою tokens.
    Менше 30 придатних документів або менше двох форматів спричиняють
    запис audit і ValueError. Версія серіалізації входить в ID набору.
    Записує UTF-8 з LF, рахує хеші з диска й оновлює current pointer.
    """
    sources = source_records(config.path("sources", root))
    documents, entries = _extract_sources(sources, root)
    chunks, block_records = _chunk_documents(documents, entries, tokens, config)
    formats = {a.format for document in documents.values() for a in document["aliases"]}
    if len(documents) < 30 or len(formats) < 2:
        audit = config.path("processed", root) / "failed" / uuid.uuid4().hex / "manifest.json"
        write_json(audit, {"status": "corpus_incomplete", "documents": len(documents), "entries": entries})
        raise ValueError(f"corpus_incomplete: {len(documents)} унікальних; формати={sorted(formats)}; "
                         f"помилки={[(e['source_id'], e.get('error')) for e in entries if e['status'] == 'error']}")
    fingerprint = {"sources": [s.model_dump(mode="json") for s in sources],
                   "artifact_serialization": ARTIFACT_SERIALIZATION,
                   "normalization": NORMALIZATION_VERSION, "extraction": EXTRACTION_VERSION, "chunking": CHUNKING_VERSION,
                   "chunk_config": {key: getattr(config, key) for key in ("target_tokens", "chunk_cap", "overlap")},
                   "assets": tokens.metadata, "entries": entries}
    dataset_id = digest(fingerprint)
    chunks = [c.model_copy(update={"dataset_id": dataset_id}) for c in chunks]
    directory = config.path("processed", root) / dataset_id
    manifest = {"dataset_id": dataset_id, "review_status": "approved", "documents": len(documents),
                "formats": sorted(formats), "chunk_count": len(chunks), "fingerprint": fingerprint}
    if directory.exists():
        existing, existing_chunks = load_dataset(directory)
        if existing["fingerprint"] != fingerprint or len(existing_chunks) != len(chunks):
            raise ValueError("dataset_incompatible: каталог уже містить інші дані")
        manifest = existing
    else:
        directory.mkdir(parents=True)
        with (directory / "chunks.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(c.model_dump_json() for c in chunks) + "\n")
        manifest["chunks_sha256"] = file_digest(directory / "chunks.jsonl")
        write_json(directory / "blocks.json", block_records)
        write_json(directory / "manifest.json", manifest)
        write_json(directory / "complete.json", {"manifest_sha256": file_digest(directory / "manifest.json")})
    write_json(directory.parent / "current.json", {"dataset_id": dataset_id}, replace=True)
    return manifest


def _extract_sources(sources: list[Source], root: Path) -> tuple[dict, list]:
    """Збирає нормалізовані унікальні документи та audit кожного original.

    Синтаксична помилка одного PDF не перериває перевірку решти файлів;
    такий source позначається error і не рахується успішним. Registry
    при цьому не переписується й approved не призначається заново.
    """
    from pdfminer.pdfexceptions import PDFException
    documents, entries = {}, []
    for source in sources:
        try:
            warnings = []
            path = within(root, source.path)
            if file_digest(path) != source.raw_sha256:
                raise ValueError("source_hash_mismatch")
            blocks = extract_html(path, source.selector) if source.format == "html" else extract_pdf(path, warnings)
            content_hash, blocks = normalize_blocks(blocks)
            duplicate = content_hash in documents
            if duplicate:
                documents[content_hash]["aliases"].append(source)
            else:
                documents[content_hash] = {"blocks": blocks, "aliases": [source]}
            entries.append({"source_id": source.source_id, "status": "duplicate" if duplicate else "ok",
                            "content_sha256": content_hash, "raw_sha256": source.raw_sha256, "warnings": warnings})
        except (ValueError, OSError, PDFException) as error:
            entries.append({"source_id": source.source_id, "status": "error", "error": str(error)})
    return documents, entries


def _chunk_documents(documents: dict, entries: list, tokens, config) -> tuple[list, list]:
    """Нарізає документи й виключає тільки явно непридатні з audit-причиною.

    Модифікує documents/entries до обчислення dataset fingerprint,
    щоб помилка довгого header не зарахувала невдалий документ у 30.
    Неповний корпус не публікується й не змінює current pointer.
    """
    chunks, block_records = [], []
    for content_hash, document in sorted(documents.items()):
        try:
            parts = make_chunks(document["blocks"], document["aliases"], content_hash, tokens, config)
            if not parts:
                raise ValueError("Документ не містить придатних чанків")
        except ValueError as error:
            del documents[content_hash]
            for entry in entries:
                if entry.get("content_sha256") == content_hash:
                    entry.update(status="error", error=str(error))
        else:
            chunks.extend(parts)
            block_records.extend(b.model_dump(mode="json") for b in document["blocks"])
    return chunks, block_records


def load_dataset(directory: Path) -> tuple[dict, list[Chunk]]:
    """Читає завершений dataset і перевіряє manifest/chunks fingerprints.

    Незавершений каталог, змінений chunk чи dataset_id відхиляються
    перед індексацією/генерацією. JSON-mode зберігає strict tuple spans.
    """
    completion = read_json(directory / "complete.json")
    if file_digest(directory / "manifest.json") != completion["manifest_sha256"]:
        raise ValueError("dataset_incompatible: manifest hash")
    manifest = read_json(directory / "manifest.json")
    if file_digest(directory / "chunks.jsonl") != manifest["chunks_sha256"]:
        raise ValueError("dataset_incompatible: chunks hash")
    chunks = [Chunk.model_validate_json(line) for line in (directory / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if line]
    if len(chunks) != manifest["chunk_count"] or any(c.dataset_id != manifest["dataset_id"] for c in chunks):
        raise ValueError("dataset_incompatible: IDs/count")
    blocks = [Block.model_validate(item) for item in read_json(directory / "blocks.json")]
    groups = {}
    for block in blocks:
        groups.setdefault(block.block_id.split(":b")[0], []).append(block)
    expected = {entry["content_sha256"] for entry in manifest["fingerprint"]["entries"] if entry["status"] == "ok"}
    actual = {normalize_blocks(sorted(group, key=lambda b: b.ordinal))[0] for group in groups.values()}
    if actual != expected:
        raise ValueError("dataset_incompatible: normalized blocks змінилися")
    return manifest, chunks


def current_dataset(config, root: Path) -> Path:
    """Повертає каталог, на який вказує перевірений current dataset pointer.

    Значення ID не використовується як довільний шлях: дозволено лише
    64 hex-символи. Відсутній pointer вимагає явного ingest, не auto-run.
    """
    import re
    base = config.path("processed", root)
    identifier = read_json(base / "current.json")["dataset_id"]
    if not isinstance(identifier, str) or not re.fullmatch(r"[0-9a-f]{64}", identifier):
        raise ValueError("Некоректний dataset pointer")
    return base / identifier
