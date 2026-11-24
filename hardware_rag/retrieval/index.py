"""Ізольований локальний Qdrant із fingerprint-сумісністю frozen dataset."""

import importlib.metadata
import uuid
from pathlib import Path
from ..artifacts import digest, read_json, write_json

# Одна колекція в кожному окремому каталозі index_id, без зовнішнього сервера.
COLLECTION = "hardware_rag"
# Правила lexical preprocessing входять до ідентичності індексу.
LEXICAL_VERSION = "unicode-technical-tokens-1"


def fingerprint(manifest: dict, embedder, config) -> dict:
    """Описує всі параметри, від яких залежить сумісність індексу.

    Включає dataset/chunks hashes, реальні assets і встановлені версії
    пакетів. Зміна цих даних вимагає явного index, а не auto-rebuild.
    """
    return {"dataset_id": manifest["dataset_id"], "chunks_sha256": manifest["chunks_sha256"],
            "embedding": embedder.metadata, "dimension": getattr(embedder, "dimension", 384),
            "lexical_version": LEXICAL_VERSION,
            "packages": {name: importlib.metadata.version(name) for name in ("qdrant-client", "fastembed", "rank-bm25")}}


def build_index(manifest: dict, chunks: list, embedder, tokens, config, root: Path) -> dict:
    """Будує новий persistent Qdrant і лише після перевірки публікує pointer.

    Існуючі індекси не видаляються й не перезаписуються. Count/fingerprint
    перевіряються до заміни current; побудова використовує тільки локальні
    embeddings assets, а не provider API.
    """
    from qdrant_client import QdrantClient, models
    identity = fingerprint(manifest, embedder, config)
    index_id = digest(identity)
    directory = config.path("indexes", root) / index_id
    if (directory / "complete.json").exists():
        if read_json(directory / "metadata.json") != identity:
            raise ValueError("index_incompatible: existing metadata")
    else:
        if directory.exists():
            raise ValueError("index_incomplete: попередня побудова не завершилася")
        directory.mkdir(parents=True)
        client = QdrantClient(path=str(directory / "qdrant"))
        try:
            client.create_collection(COLLECTION, vectors_config=models.VectorParams(
                size=identity["dimension"], distance=models.Distance.COSINE))
            for offset in range(0, len(chunks), 32):
                batch = chunks[offset:offset + 32]
                vectors = embedder.encode([tokens.passage(c.title, c.section, c.text) for c in batch])
                points = [models.PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL, c.chunk_id)),
                          vector=v, payload={"chunk_id": c.chunk_id, "language": c.language,
                          "formats": sorted({a.format for a in c.aliases})}) for c, v in zip(batch, vectors)]
                client.upsert(COLLECTION, points=points, wait=True)
            if client.count(COLLECTION, exact=True).count != len(chunks):
                raise ValueError("index_incomplete: count mismatch")
        finally:
            client.close()
        write_json(directory / "metadata.json", identity)
        write_json(directory / "complete.json", {"metadata_sha256": digest(identity)})
    write_json(directory.parent / "current.json", {"index_id": index_id}, replace=True)
    return {"index_id": index_id, "chunks": len(chunks), "identity": identity}


def open_index(manifest: dict, chunks: list, embedder, config, root: Path):
    """Відкриває тільки поточний завершений індекс із точним fingerprint.

    Змішаний dataset/model/tokenizer/package profile відхиляє до query.
    Повернений QdrantClient необхідно закрити після роботи; метод ніколи
    не створює відсутню базу як порожню заміну потрібного індексу.
    """
    from qdrant_client import QdrantClient
    identity = fingerprint(manifest, embedder, config)
    index_id = digest(identity)
    base = config.path("indexes", root)
    if read_json(base / "current.json").get("index_id") != index_id:
        raise ValueError("index_incompatible: dataset/model/config змінилися")
    directory = base / index_id
    if read_json(directory / "complete.json").get("metadata_sha256") != digest(identity):
        raise ValueError("index_incompatible: completion hash")
    if read_json(directory / "metadata.json") != identity or not (directory / "qdrant").is_dir():
        raise ValueError("index_incompatible: metadata/storage")
    client = QdrantClient(path=str(directory / "qdrant"))
    if client.count(COLLECTION, exact=True).count != len(chunks):
        client.close()
        raise ValueError("index_incompatible: chunk count")
    return client
