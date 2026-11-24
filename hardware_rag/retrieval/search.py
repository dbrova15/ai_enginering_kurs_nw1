"""BM25, vector і RRF над одним набором чанків з однаковими фільтрами."""

import re
from .index import COLLECTION

# Unicode-слова й технічні сполуки: ESP32-S3, USB-C, 3.3 не розпадаються.
TECHNICAL_TOKEN = re.compile(r"[^\W_]+(?:[-+./][^\W_]+)*", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Повертає casefold-токени без перекладу, стемінгу чи втрати кодів.

    Оригінальний chunk text не змінює; уніфікація потрібна тільки
    lexical matching. Unicode дозволяє спільний код для uk/en/ru.
    """
    return TECHNICAL_TOKEN.findall(text.casefold())


def allowed(chunk, language: str | None = None, document_format: str | None = None) -> bool:
    """Перевіряє AND-фільтр мови та формату з урахуванням усіх aliases.

    Порожнє значення означає відсутність відповідного фільтра. PDF alias
    не губиться, якщо canonical source мав інший формат.
    """
    return (language is None or chunk.language == language) and (
        document_format is None or any(a.format == document_format for a in chunk.aliases))


def bm25_search(chunks: list, question: str, limit: int) -> list[dict]:
    """Рахує BM25 над уже відфільтрованою підмножиною й повертає candidates.

    Кандидати без жодного lexical overlap не додаються як випадкові
    нульові збіги. Негативні, але справжні BM25 scores не відкидаються;
    однакові значення стабілізуються chunk_id.
    """
    from rank_bm25 import BM25Okapi
    query = tokenize(question)
    corpus = [tokenize(c.title + " " + c.section + " " + c.text) for c in chunks]
    if not chunks or not query or not any(corpus):
        return []
    scores = BM25Okapi(corpus).get_scores(query)
    hits = [{"chunk": c, "score": float(score)} for c, words, score in zip(chunks, corpus, scores)
            if set(query).intersection(words)]
    return sorted(hits, key=lambda h: (-h["score"], h["chunk"].chunk_id))[:limit]


def rrf(rankings: list[list[dict]], limit: int, constant: int = 60) -> list[dict]:
    """Об'єднує списки за рангами, не складаючи несумісні raw scores.

    Один chunk рахується максимум раз у кожному каналі; rank починається
    з 1. Повертає deduplicated candidates зі стабільним порядком ties.
    """
    merged = {}
    for ranking in rankings:
        seen = set()
        for rank, hit in enumerate(ranking, 1):
            key = hit["chunk"].chunk_id
            if key in seen:
                continue
            seen.add(key)
            item = merged.setdefault(key, {"chunk": hit["chunk"], "score": 0.0})
            item["score"] += 1 / (constant + rank)
    return sorted(merged.values(), key=lambda h: (-h["score"], h["chunk"].chunk_id))[:limit]


class Retriever:
    """Виконує три порівнювані режими з однаковими даними й фільтрами.

    Приймає відкритий index, embedder/tokenizer і необов'язковий reranker;
    не створює файли чи моделі самостійно. Клієнтом володіє caller.
    """
    def __init__(self, chunks: list, client, embedder, tokens, config, reranker=None):
        """Запам'ятовує перевірені залежності та карту frozen chunk IDs.

        Валідацію fingerprint виконує open_index перед створенням цього
        об'єкта. Fake dependencies допустимі тільки в офлайн-тестах.
        """
        self.chunks, self.client, self.embedder = chunks, client, embedder
        self.tokens, self.config, self.reranker = tokens, config, reranker
        self.by_id = {c.chunk_id: c for c in chunks}

    def search(self, question: str, language=None, document_format=None, mode=None) -> list[dict]:
        """Повертає top-k після vector/RRF/rerank, не послаблюючи фільтри.

        Порожня дозволена підмножина повертає []; неправильний mode чи
        відсутній reranker для hybrid+rerank — явна помилка, не fallback.
        """
        from qdrant_client import models
        mode = mode or self.config.retrieval
        if mode not in ("vector", "hybrid", "hybrid+rerank"):
            raise ValueError("Невідома retrieval-конфігурація")
        query = self.tokens.query(question, self.config.query_cap)
        subset = [c for c in self.chunks if allowed(c, language, document_format)]
        if not subset:
            return []
        conditions = []
        if language:
            conditions.append(models.FieldCondition(key="language", match=models.MatchValue(value=language)))
        if document_format:
            conditions.append(models.FieldCondition(key="formats", match=models.MatchValue(value=document_format)))
        points = self.client.query_points(COLLECTION, query=self.embedder.encode([query])[0],
                   query_filter=models.Filter(must=conditions) if conditions else None,
                   limit=self.config.candidates).points
        vector = [{"chunk": self.by_id[p.payload["chunk_id"]], "score": float(p.score)} for p in points]
        if any(not allowed(h["chunk"], language, document_format) for h in vector):
            raise ValueError("Індекс порушив metadata-фільтр")
        if mode == "vector":
            return vector[:self.config.k]
        candidates = rrf([vector, bm25_search(subset, question, self.config.candidates)],
                         self.config.candidates, self.config.rrf_constant)
        if mode == "hybrid":
            return candidates[:self.config.k]
        if self.reranker is None:
            raise ValueError("Reranker не підготовлено; fallback заборонено")
        return self.reranker.rank(question, candidates, self.config.k)
