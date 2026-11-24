"""Локальний Qdrant/BM25/RRF без ваг моделей чи зовнішньої мережі."""

import tempfile
import unittest
from pathlib import Path
from hardware_rag.artifacts import read_json
from hardware_rag.config import RagConfig
from hardware_rag.retrieval.index import build_index, open_index
from hardware_rag.retrieval.search import allowed, bm25_search, rrf, tokenize, Retriever
from rag_fixtures import FakeEmbedding, Words, chunk, source


class RetrievalTests(unittest.TestCase):
    """Перевіряє правила ranking, metadata-фільтрів і сумісності index.

    Вектори аналітичні, тому ці тести не є виміром semantic retrieval.
    Реальні метрики обчислюються окремим прогоном frozen тестсету.
    """
    def test_technical_tokens_and_alias_filters(self):
        """Технічні коди не розпадаються, PDF alias зберігає доступність.

        AND-фільтр мови й формату не підміняється одним лише форматом.
        """
        self.assertIn("esp32-s3", tokenize("ESP32-S3 uses USB-C at 3.3 V"))
        c = chunk(aliases=[source(), source(source_id="pdf", format="pdf", path="test.pdf")])
        self.assertTrue(allowed(c, "uk", "pdf"))
        self.assertFalse(allowed(c, "en", "pdf"))
        self.assertEqual(c.source_for("pdf").source_id, "pdf")
        with self.assertRaises(ValueError):
            chunk().source_for("pdf")

    def test_rrf_deduplicates_each_channel_and_stabilizes_ties(self):
        """Повторний ID одного каналу не повинен штучно піднімати score.

        Порожні rankings допустимі; tie порядок задає chunk_id.
        """
        a, b = chunk("a"), chunk("b")
        hits = rrf([[{"chunk": a}, {"chunk": a}], [{"chunk": b}]], 5)
        self.assertEqual([h["chunk"].chunk_id for h in hits], ["a", "b"])
        self.assertAlmostEqual(hits[0]["score"], hits[1]["score"])
        self.assertEqual(rrf([[], []], 5), [])

    def test_bm25_does_not_return_arbitrary_zero_overlap(self):
        """Питання без lexical overlap не створює випадкові BM25 hits.

        Точний рідкісний код усе ще знаходиться без embeddings.
        """
        c = chunk(text="The unique code is ESP32-S3.")
        self.assertEqual(bm25_search([c], "unrelatedxyz", 5), [])
        self.assertEqual(bm25_search([c], "ESP32-S3", 5)[0]["chunk"].chunk_id, "c1")

    def test_qdrant_round_trip_filters_and_stale_model(self):
        """Persistent index працює з vector фільтром і відхиляє нову модель.

        Для перевірки використовуються 3D fake vectors, ніяких downloads.
        Повторний build сумісного index не перезаписує існуючу базу.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = RagConfig(indexes="indexes")
            manifest = {"dataset_id": "dataset", "chunks_sha256": "hash"}
            chunks = [chunk("wifi"), chunk("resistor", "resistor 100 ohm", language="en",
                       aliases=[source(source_id="en-pdf", language="en", format="pdf")])]
            embedder, tokens = FakeEmbedding(), Words()
            built = build_index(manifest, chunks, embedder, tokens, config, root)
            self.assertEqual(built["chunks"], 2)
            client = open_index(manifest, chunks, embedder, config, root)
            try:
                retriever = Retriever(chunks, client, embedder, tokens, config)
                found = retriever.search("Wi-Fi", "uk", "html", mode="vector")
                self.assertEqual([h["chunk"].chunk_id for h in found], ["wifi"])
                self.assertEqual(retriever.search("Wi-Fi", "ru", mode="vector"), [])
                with self.assertRaisesRegex(ValueError, "Reranker"):
                    retriever.search("Wi-Fi", mode="hybrid+rerank")
            finally:
                client.close()
            self.assertEqual(build_index(manifest, chunks, embedder, tokens, config, root)["index_id"], built["index_id"])
            embedder.metadata = {"synthetic_model": "axes-2"}
            with self.assertRaisesRegex(ValueError, "index_incompatible"):
                open_index(manifest, chunks, embedder, config, root)
