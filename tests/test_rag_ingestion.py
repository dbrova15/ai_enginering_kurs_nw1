"""Офлайн-перевірки реального HTML/PDF parsing, нормалізації й proof spans."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from hardware_rag.config import RagConfig
from hardware_rag.documents import Block
from hardware_rag.ingestion.html import extract_html
from hardware_rag.ingestion.pdf import extract_pdf, _table_rows
from hardware_rag.ingestion.normalize import normalize_blocks
from hardware_rag.ingestion.chunking import make_chunks
from hardware_rag.artifacts import digest, file_digest, read_json, write_json, within
from hardware_rag.ingestion.pipeline import ingest, load_dataset
from rag_fixtures import Words, source, minimal_pdf


class IngestionTests(unittest.TestCase):
    """Перевіряє втрату структури й відтворюваність на малих контрольних input.

    Fixtures не є golden set ДЗ2; результати не використовуються
    для звіту про реальну точність чи кількість документів корпусу.
    """
    def test_html_outer_layout_table_does_not_remove_article(self):
        """Відтворює знайдену помилку arduino.ua з outer table layout.

        Внутрішня content table і pre зберігаються по одному разу,
        навігація та вкладені table paragraphs не дублюються.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.html"
            path.write_text('<table><tr><td><article><h1>Chip</h1><nav>noise</nav><p>3.3 V</p><table><tr><th>Pin</th><th>Value</th></tr><tr><td>1</td><td><p>5 V</p></td></tr></table><pre>  int x;\n    x++;</pre></article></td></tr></table>', encoding="utf-8", newline="\n")
            blocks = extract_html(path)
            self.assertEqual([b.kind for b in blocks], ["heading", "paragraph", "table", "code"])
            self.assertIn("Pin | Value", blocks[2].text)
            self.assertEqual(blocks[-1].text, "  int x;\n    x++;")

    def test_pdf_short_cover_is_not_whole_document_ocr_failure(self):
        """Коротка текстова обкладинка лишає audit, але не відкидає PDF.

        Друга сторінка має достатньо тексту. Справжній parser підтверджує
        номери сторінок без mocked extract_text.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.pdf"
            path.write_bytes(minimal_pdf(["Cover", "ESP32 technical document. Wi-Fi and power supply 3.3 V are described in this section."]))
            audit = []
            blocks = extract_pdf(path, audit)
            self.assertIn("low_text_page:1", audit[0])
            self.assertEqual({b.page_start for b in blocks}, {1, 2})

    def test_legacy_paragraph_code_keeps_literal_spaces_and_line_breaks(self):
        """Скетч у HTML <p> зберігає значущі пробіли після normalization.

        Відтворює HR-0038 LCD literal; inline spans не розривають код,
        <br> лишає окремі рядки, а Wi-Fi проза не стає assignment-кодом.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.html"
            path.write_text('<article><p>Wi-Fi uses 3.3 V.</p><p>\t#include &lt;LCD.h&gt;</p><p>\t<span>lcd</span>.print("    TERMOBOX");<br>\t  lcd.clear();<br>else digitalWrite(1,LOW);</p><p>Пояснення роботи.</p></article>', encoding="utf-8")
            _, blocks = normalize_blocks(extract_html(path))
            self.assertEqual([b.kind for b in blocks], ["paragraph", "code", "code", "paragraph"])
            self.assertEqual(blocks[2].text, '\tlcd.print("    TERMOBOX");\n\t  lcd.clear();\nelse digitalWrite(1,LOW);')

    def test_unreadable_pdf_needs_ocr(self):
        """Увесь PDF без придатного шару відхиляється, не рахується як corpus.

        Це окремо від короткої обкладинки читабельного документа.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.pdf"
            path.write_bytes(minimal_pdf([""]))
            with self.assertRaisesRegex(ValueError, "needs_ocr"):
                extract_pdf(path)

    def test_normalization_keeps_code_units_and_deterministic_ids(self):
        """NFC/пробіли прозового тексту не змінюють код, мінуси чи одиниці.

        Однаковий input повторює content hash і block IDs; зміна числа
        повинна змінити ідентичність, а не загубитися в cleanup.
        """
        blocks = [Block(block_id="0", ordinal=0, kind="paragraph", text="3.3  V −15 °C", section="S"),
                  Block(block_id="1", ordinal=1, kind="code", text="  x = 3;\n    y++;", section="S")]
        first, cleaned = normalize_blocks(blocks)
        self.assertEqual(first, normalize_blocks(blocks)[0])
        self.assertEqual(cleaned[1].text, blocks[1].text)
        changed = blocks[0].model_copy(update={"text": "5 V"})
        self.assertNotEqual(first, normalize_blocks([changed, blocks[1]])[0])

    def test_chunkers_keep_spans_caps_and_identity(self):
        """Обидві стратегії покривають текст і посилаються на дійсні offsets.

        Header теж урахований у cap; fixed і heading мають різні IDs.
        Не перевіряє реальну семантичну перевагу однієї стратегії.
        """
        config = RagConfig(target_tokens=32, chunk_cap=48, overlap=4)
        tokens = Words()
        _, blocks = normalize_blocks([Block(block_id="b", ordinal=0, kind="paragraph", text=" ".join(f"word{i}" for i in range(100)), section="S")])
        heading = make_chunks(blocks, [source()], "hash", tokens, config)
        fixed = make_chunks(blocks, [source()], "hash", tokens, config, fixed=True)
        self.assertGreater(len(heading), 1)
        for c in heading + fixed:
            self.assertLessEqual(tokens.count(tokens.passage(c.title, c.section, c.text)), 48)
            for block_id, start, end in c.spans:
                self.assertEqual(block_id, blocks[0].block_id)
                self.assertTrue(0 <= start < end <= len(blocks[0].text))
        self.assertNotEqual(heading[0].chunk_id, fixed[0].chunk_id)
        self.assertEqual(heading[0].chunk_id, make_chunks(blocks, [source()], "hash", tokens, config)[0].chunk_id)

    def test_atomic_records_never_overwrite_history(self):
        """Immutable write відхиляє повторний шлях; pointer replacement явний.

        Також перевіряє захист path traversal за межі workspace.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "record.json"
            write_json(path, {"a": 1})
            with self.assertRaises(FileExistsError):
                write_json(path, {"a": 2})
            self.assertEqual(read_json(path), {"a": 1})
            write_json(path, {"a": 2}, replace=True)
            self.assertEqual(read_json(path), {"a": 2})
            with self.assertRaises(ValueError):
                within(root, "../escape")
            self.assertEqual(digest({"x": 1, "y": 2}), digest({"y": 2, "x": 1}))

    def test_long_table_repeats_real_header_with_exact_spans(self):
        """Після поділу довгої таблиці кожний chunk має початкові колонки.

        Повторений header посилається на оригінальний span; жодного
        рядка таблиці не вигадано для зручності LLM.
        """
        block = Block(block_id="table", ordinal=0, kind="table", section="S",
                      text="Pin | Value\n" + "\n".join(f"{i} | value{i}" for i in range(40)))
        _, blocks = normalize_blocks([block])
        chunks = make_chunks(blocks, [source()], "hash", Words(), RagConfig(target_tokens=32, chunk_cap=48, overlap=4))
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(c.text.startswith("Pin | Value\n") for c in chunks))
        self.assertTrue(all(c.spans[0][1] == 0 for c in chunks))

    def test_pdf_merged_cell_fills_only_with_geometric_proof(self):
        """Вертикальний rowspan успадковує текст, справжній blank — ні.

        Це перевіряє знайдений на ESP32 DC table зв'язок струму IOH
        із кількома power domains, без сліпого fill-forward клітинок.
        """
        rows = [SimpleNamespace(bbox=(0, 0, 20, 20), cells=[(0, 0, 10, 20), (10, 0, 20, 10)]),
                SimpleNamespace(bbox=(0, 10, 20, 20), cells=[None, (10, 10, 20, 20)]),
                SimpleNamespace(bbox=(0, 20, 20, 30), cells=[None, (10, 20, 20, 30)])]
        table = SimpleNamespace(rows=rows, extract=lambda **kwargs: [["IOH", "CPU"], [None, "RTC"], [None, "blank"]])
        result = _table_rows(table)
        self.assertEqual(result[1], ["IOH", "RTC"])
        self.assertEqual(result[2], [None, "blank"])

    def test_complete_ingestion_preserves_previous_pointer_below_minimum(self):
        """Справжній малий HTML/PDF E2E перевіряє counts, audit й rollback.

        31 синтетичний original дає dataset; після двох hash failures
        лишається 29 і новий current не публікується. Попередній запис
        залишається читабельним. Перевіряє LF, версію запису й хеші байтів.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = []
            for i in range(30):
                path = root / f"doc{i}.html"
                path.write_text(f"<article><h1>Device {i}</h1><p>Device {i} uses 3.3 V and unique technical input.</p></article>", encoding="utf-8")
                sources.append(source(source_id=f"html-{i}", path=path.name, raw_sha256=file_digest(path)))
            pdf = root / "technical.pdf"
            pdf.write_bytes(minimal_pdf(["The PDF technical device is a separate document describing a 3.3 V power supply and GPIO."]))
            sources.append(source(source_id="pdf", path=pdf.name, format="pdf", language="en", raw_sha256=file_digest(pdf)))
            write_json(root / "sources.json", {"review_status": "approved", "sources": [s.model_dump(mode="json") for s in sources]})
            config = RagConfig(sources="sources.json", processed="processed")
            first = ingest(config, Words(), root)
            self.assertEqual(first["documents"], 31)
            self.assertEqual(first["fingerprint"]["artifact_serialization"], "utf8-lf")
            directory = root / "processed" / first["dataset_id"]
            for name in ("chunks.jsonl", "blocks.json", "manifest.json", "complete.json"):
                with self.subTest(artifact=name):
                    payload = (directory / name).read_bytes()
                    self.assertNotIn(b"\r", payload)
                    self.assertTrue(payload.endswith(b"\n"))
            self.assertEqual(first["chunks_sha256"], file_digest(directory / "chunks.jsonl"))
            self.assertEqual(read_json(directory / "complete.json")["manifest_sha256"],
                             file_digest(directory / "manifest.json"))
            self.assertEqual(first["dataset_id"], ingest(config, Words(), root)["dataset_id"])
            for i in (0, 1):
                (root / f"doc{i}.html").write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "corpus_incomplete"):
                ingest(config, Words(), root)
            self.assertEqual(read_json(root / "processed/current.json")["dataset_id"], first["dataset_id"])
            self.assertEqual(load_dataset(directory)[0]["documents"], 31)
            audits = list((root / "processed/failed").glob("*/manifest.json"))
            self.assertEqual(len(audits), 1)
            self.assertEqual(sum(e["status"] == "error" for e in read_json(audits[0])["entries"]), 2)
