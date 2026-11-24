"""Адаптер погодженого multilingual E5 поверх локального FastEmbed/ONNX."""

from pathlib import Path
from .assets import MODEL_SPECS

# Менший CPU batch обмежує activations і тимчасовий int64 mask mean pooling.
# Batch 16 вичерпав доступну Windows commit memory; 4 входить до metadata,
# тому індекс із цим runtime-профілем має власний fingerprint.
EMBEDDING_BATCH_SIZE = 4


class Embedder:
    """Перетворює вже підготовлені prefixed strings на нормалізовані вектори.

    Не додає prefix вдруге та не отримує файлів із мережі. Модель
    створюється лише після перевірки assets у переданому ModelTokens.
    """
    def __init__(self, assets: Path, tokens):
        """Реєструє E5 через public custom-model API й читає локальний ONNX.

        Використовує mean pooling/normalization/384 dimensions із model
        card. specific_model_path запобігає автоматичному model download.
        """
        from fastembed import TextEmbedding
        from fastembed.common.model_description import ModelSource, PoolingType
        spec = MODEL_SPECS["embedding"]
        if spec["model"] not in {m["model"] for m in TextEmbedding.list_supported_models()}:
            TextEmbedding.add_custom_model(model=spec["model"], pooling=PoolingType.MEAN,
                                           normalization=True, dim=384,
                                           sources=ModelSource(hf=spec["repo"]), model_file=spec["file"])
        self.tokens = tokens
        self.metadata = {**tokens.metadata["embedding"], "inference_batch_size": EMBEDDING_BATCH_SIZE,
                         "enable_cpu_mem_arena": False}
        # Public option звільняє CPU allocations замість утримання великих arenas.
        self.model = TextEmbedding(spec["model"], specific_model_path=str(assets / "embedding"),
                                   providers=["CPUExecutionProvider"], threads=4, enable_cpu_mem_arena=False)

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Обчислює вектори списку готових query:/passage: inputs.

        Відхиляє непорожній input без префікса та понад 512 токенів,
        перевіряє форму й скінченність вихідних 384-вимірних векторів.
        """
        import math
        if any(not t.startswith(("query: ", "passage: ")) or self.tokens.count(t) > 512 for t in texts):
            raise ValueError("Некоректний E5 input або токенний ліміт")
        vectors = [v.tolist() for v in self.model.embed(texts, batch_size=EMBEDDING_BATCH_SIZE)] if texts else []
        if len(vectors) != len(texts) or any(len(v) != 384 or not all(math.isfinite(x) for x in v) for v in vectors):
            raise ValueError("Embedding model повернула невалідні вектори")
        return vectors
