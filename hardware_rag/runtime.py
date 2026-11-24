"""Збирання перевірених залежностей без змішування алгоритмів CLI та моделей."""

from contextlib import contextmanager
from pathlib import Path
from .ingestion.pipeline import current_dataset, load_dataset
from .retrieval.tokenization import ModelTokens
from .retrieval.embeddings import Embedder
from .retrieval.rerank import Reranker
from .retrieval.index import open_index
from .retrieval.search import Retriever
from .generation.budget import Budget


@contextmanager
def retrieval_runtime(config, root: Path, *, rerank: bool = True):
    """Відкриває сумісний dataset/index/models і гарантовано закриває Qdrant.

    Повертає manifest, chunks та Retriever. Відсутній current або assets
    є явною помилкою: ця фабрика не виконує ingestion/download/rebuild.
    """
    manifest, chunks = load_dataset(current_dataset(config, root))
    tokens = ModelTokens(config.path("assets", root))
    embedder = Embedder(config.path("assets", root), tokens)
    ranker = Reranker(config.path("assets", root), tokens) if rerank else None
    client = open_index(manifest, chunks, embedder, config, root)
    try:
        yield manifest, chunks, Retriever(chunks, client, embedder, tokens, config, ranker)
    finally:
        client.close()


def approved_budget(config) -> Budget:
    """Створює shared per-run Budget тільки з явно заповненого paid profile.

    Ключів тут немає; сам Budget не дозволяє API, а доповнює перевірку
    paid_enabled у LlmClient. Невідомі тарифи/дата блокують запуск.
    """
    if not config.paid_enabled or config.budget_usd is None or config.pricing_date is None:
        raise ValueError("Платний профіль/бюджет не погоджений")
    if config.input_usd_per_million is None or config.output_usd_per_million is None:
        raise ValueError("Тарифи невідомі; оцінка нульової ціни заборонена")
    return Budget(config.budget_usd, config.input_usd_per_million, config.output_usd_per_million)
