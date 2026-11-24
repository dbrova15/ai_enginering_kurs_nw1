"""Cross-encoder reranking без підміни моделі чи тихого hybrid fallback."""

from pathlib import Path
from .assets import MODEL_SPECS


class Reranker:
    """Оцінює питання разом із кожним кандидатом і зберігає chunk mapping.

    Обрана multilingual BGE INT8 реєструється public API, якщо відсутня
    у registry встановленого FastEmbed. Ваги читаються тільки локально.
    """
    def __init__(self, assets: Path, tokens):
        """Створює CPU cross-encoder з перевірених локальних model assets.

        Не завантажує нові файли. Переданий tokens уже перевірив їхні
        SHA-256, а metadata використовується для lineage оцінювання.
        """
        from fastembed.rerank.cross_encoder import TextCrossEncoder
        from fastembed.common.model_description import ModelSource
        spec = MODEL_SPECS["reranker"]
        if spec["model"] not in {m["model"] for m in TextCrossEncoder.list_supported_models()}:
            TextCrossEncoder.add_custom_model(model=spec["model"], sources=ModelSource(hf=spec["repo"]),
                                              model_file=spec["file"], license="apache-2.0")
        self.tokens = tokens
        # Не утримувати великі CPU arenas між запитами на shared workstation.
        self.model = TextCrossEncoder(spec["model"], specific_model_path=str(assets / "reranker"),
                                      providers=["CPUExecutionProvider"], threads=4, enable_cpu_mem_arena=False)

    def rank(self, question: str, hits: list[dict], k: int) -> list[dict]:
        """Повертає top-k кандидатів після перевірки exact pair-token cap.

        Score cross-encoder не є імовірністю. При помилці inference
        метод падає явно; tie стабілізується chunk_id, IDs не змінюються.
        """
        import math
        for hit in hits:
            self.tokens.pair(question, hit["chunk"].text)
        scores = list(self.model.rerank(question, [h["chunk"].text for h in hits], batch_size=4)) if hits else []
        if len(scores) != len(hits) or not all(math.isfinite(float(v)) for v in scores):
            raise ValueError("Некоректні reranker scores")
        ranked = [{**hit, "score": float(score)} for hit, score in zip(hits, scores)]
        return sorted(ranked, key=lambda h: (-h["score"], h["chunk"].chunk_id))[:k]
