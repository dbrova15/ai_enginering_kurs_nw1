"""Exact token counts локальних моделей без прихованого обрізання input."""

from pathlib import Path
from .assets import verify_assets


class ModelTokens:
    """Лічильник обох модельних tokenizer, що читає тільки локальні assets.

    Розрізняє passage із заголовком та query з E5-prefix. Обидва
    tokenizer працюють без truncation; вміщення не оцінюється символами.
    """
    def __init__(self, assets: Path):
        """Перевіряє fingerprints і завантажує два tokenizer.json.

        Не ініціалізує ONNX inference і не викликає API; при відсутніх
        assets завершується помилкою без мережевого fallback.
        """
        from tokenizers import Tokenizer
        self.metadata = verify_assets(assets)
        self.tokenizers = {}
        for role in ("embedding", "reranker"):
            tokenizer = Tokenizer.from_file(str(assets / role / "tokenizer.json"))
            tokenizer.no_truncation()
            tokenizer.no_padding()
            self.tokenizers[role] = tokenizer

    def count(self, text: str) -> int:
        """Повертає більший exact count двох tokenizer з special tokens.

        Використовується для hard caps чанків і запитів. Більший count
        запобігає проходженню тексту лише за зручнішим tokenizer.
        """
        return max(len(t.encode(text).ids) for t in self.tokenizers.values())

    def passage(self, title: str, section: str, text: str) -> str:
        """Створює E5 passage із справжніх metadata та незміненого тексту.

        Title/section скорочуються до обмеженого представлення, але
        повні поля лишаються в Chunk. Це не contextual headers від LLM.
        """
        header = f"{title} / {section}"
        while self.count(header) > 48:
            header = header[:max(1, len(header) * 3 // 4)]
        return f"passage: {header}\n{text}"

    def fits(self, title: str, section: str, text: str, cap: int) -> bool:
        """Перевіряє повний passage проти cap, включно з prefix/metadata.

        Порожній текст не є придатним фрагментом. Метод нічого не
        обрізає й дозволяє chunker вибрати іншу точну межу доказу.
        """
        return bool(text.strip()) and self.count(self.passage(title, section, text)) <= cap

    def query(self, question: str, cap: int) -> str:
        """Валідовує довжину питання і повертає рівно один E5 query-prefix.

        Занадто довгий або порожній запит є помилкою користувацького
        input. Довжина не зменшується приховано перед пошуком.
        """
        if not question.strip() or self.count("query: " + question) > cap:
            raise ValueError("Порожнє або задовге питання для retrieval")
        return "query: " + question

    def pair(self, question: str, passage: str, cap: int = 512) -> None:
        """Перевіряє точний pair input reranker перед inference.

        Обидві частини й special tokens ураховано одним encoding;
        перевищення cap дає помилку, а не обрізання релевантного доказу.
        """
        tokenizer = self.tokenizers["reranker"]
        if len(tokenizer.encode(question, passage).ids) > cap:
            raise ValueError("Reranker pair перевищує токенний ліміт")
