"""Перевірки запуску, конфігурації й JSONL без зовнішньої мережі."""

import hashlib
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import httpx
from openai import OpenAI

import main
from test_extract import EXPECTED


class ConfigurationTests(unittest.TestCase):
    def test_model_configuration_for_each_provider(self):
        cases = [
            ({"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test", "OPENAI_MODEL": "custom"},
             ("https://api.openai.com/v1", "test", "custom")),
            ({"LLM_PROVIDER": "openrouter", "OPENROUTER_API_KEY": "test"},
             ("https://openrouter.ai/api/v1", "test", "openai/gpt-4o-mini")),
            ({"LLM_PROVIDER": "ollama", "OLLAMA_BASE_URL": "http://localhost:11434/v1/"},
             ("http://localhost:11434/v1", "ollama", "llama3.2:3b")),
        ]
        for environment, expected in cases:
            with self.subTest(environment=environment), patch.dict(os.environ, environment, clear=True), \
                    patch("main.LLM_PROVIDER", environment["LLM_PROVIDER"]):
                self.assertEqual(main.load_model(), expected)

    def test_missing_key_and_unknown_provider_fail_before_request(self):
        for environment in ({"LLM_PROVIDER": "openai"}, {"LLM_PROVIDER": "unknown"}):
            with self.subTest(environment=environment), patch.dict(os.environ, environment, clear=True), \
                    patch("main.LLM_PROVIDER", environment["LLM_PROVIDER"]):
                with self.assertRaises(ValueError):
                    main.load_model()

    def test_real_paths_prompt_encoding_and_full_hash(self):
        self.assertEqual(main.ROOT, Path(main.__file__).resolve().parent)
        self.assertTrue(main.GOLDEN.is_file())
        for version in ("v1", "v2"):
            text, digest = main.load_prompt(version)
            self.assertIn("статті", text)
            self.assertEqual(digest, hashlib.sha256(text.encode("utf-8")).hexdigest())

    def test_preparation_preserves_body_title_and_line_endings(self):
        text = "Заголовок\r\n\r\nАвтори: X\r\n\r\nКатегорії: Arduino\r\n\r\nПлати: Uno\r\n\r\nКод\r\nКатегорії: зміст\r\n"
        self.assertEqual(main.prepare_text(text), "Заголовок\r\n\r\nКод\r\nКатегорії: зміст\r\n")
        for unchanged in ("", "Заголовок\nТекст\n", "Заголовок\nАвтори: X\nТекст", "Заголовок\nТекст\nАвтори: X\nКатегорії: Y\nПлати: Z\n"):
            with self.subTest(text=unchanged):
                self.assertEqual(main.prepare_text(unchanged), unchanged)

    def test_arguments_default_to_baseline_without_schema_selection(self):
        args = main.parse_args([])
        self.assertEqual(args.prompt_version, "v1")
        self.assertIsNone(args.limit)
        self.assertIsNone(args.output)
        self.assertFalse(hasattr(args, "schema_version"))

    def test_nonpositive_limit_is_rejected(self):
        for limit in ("0", "-1"):
            with self.subTest(limit=limit), patch("sys.stderr", new_callable=io.StringIO):
                with self.assertRaises(SystemExit) as error:
                    main.parse_args(["--limit", limit])
                self.assertEqual(error.exception.code, 2)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.texts = self.root / "texts"
        for language in ("en", "ru", "uk"):
            (self.texts / language).mkdir(parents=True)
        self.source = b"Title\r\n\r\n" + "Автори: X\r\n\r\nКатегорії: hidden-label\r\n\r\nПлати: hidden-board\r\n\r\nBody\r\n".encode("utf-8")
        (self.texts / "en" / "HR-1.txt").write_bytes(self.source)
        (self.texts / "ru" / "HR-2.txt").write_text("Стаття", encoding="utf-8")
        self.output = self.root / "results.jsonl"
        self.requests = []

    def handle_request(self, request):
        self.requests.append(json.loads(request.content))
        refused = len(self.requests) == 1
        return httpx.Response(200, json={
            "id": "test-completion", "object": "chat.completion", "created": 0,
            "model": "test-model",
            "choices": [{"index": 0, "finish_reason": "stop", "message": {
                "role": "assistant", "content": None if refused else json.dumps(EXPECTED),
                "refusal": "Відмова" if refused else None,
            }}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        })

    def run_pipeline(self, *arguments, environment=None):
        client = OpenAI(api_key="test", base_url="https://unit.test/v1",
                        http_client=httpx.Client(transport=httpx.MockTransport(self.handle_request)))
        self.addCleanup(client.close)
        configuration = {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test"}
        configuration.update(environment or {})
        with patch.dict(os.environ, configuration, clear=True), \
                patch("main.LLM_PROVIDER", configuration["LLM_PROVIDER"].strip().lower()), \
                patch("main.TEXTS", self.texts), patch("main.OpenAI", return_value=client), \
                redirect_stdout(io.StringIO()):
            main.main(["v2", "--output", str(self.output), *arguments])

    def test_pipeline_saves_failure_then_success_without_leaking_metadata(self):
        self.run_pipeline()
        records = [json.loads(line) for line in self.output.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([record["document_id"] for record in records], ["HR-1", "HR-2"])
        self.assertTrue(all(record["schema_version"] == "v2" for record in records))
        self.assertEqual([record["result"]["ok"] for record in records], [False, True])
        self.assertEqual(records[0]["source_sha256"], hashlib.sha256(self.source).hexdigest())
        sent = self.requests[0]["messages"][-1]["content"]
        self.assertNotIn("hidden-label", sent)
        self.assertNotIn("hidden-board", sent)
        self.assertIn("Title", sent)
        self.assertIn("Body", sent)
        self.assertEqual(records[0]["input_sha256"], hashlib.sha256(sent.encode("utf-8")).hexdigest())
        self.assertEqual(self.requests[0]["response_format"]["json_schema"]["name"], "DevicePosting")
        self.assertEqual(self.requests[0]["temperature"], 0)
        self.assertEqual(self.requests[0]["top_p"], 1)
        self.assertNotIn("max_tokens", self.requests[0])
        self.assertNotIn("max_tokens", records[0]["sampling"])
        self.assertEqual((self.texts / "en" / "HR-1.txt").read_bytes(), self.source)
        self.assertNotIn("api_key", records[0])

    def test_limit_restricts_requests(self):
        self.run_pipeline("--limit", "1")
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(len(self.output.read_text(encoding="utf-8").splitlines()), 1)

    def test_explicit_max_tokens_is_sent_and_logged(self):
        self.run_pipeline("--limit", "1", environment={"MAX_TOKENS": "128"})
        self.assertEqual(self.requests[0]["max_tokens"], 128)
        record = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(record["sampling"]["max_tokens"], 128)

    def test_blank_max_tokens_is_omitted(self):
        self.run_pipeline("--limit", "1", environment={"MAX_TOKENS": " \t"})
        self.assertNotIn("max_tokens", self.requests[0])

    def test_invalid_max_tokens_fails_before_request(self):
        for value in ("0", "-1", "invalid"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_pipeline(environment={"MAX_TOKENS": value})
        self.assertEqual(self.requests, [])
        self.assertFalse(self.output.exists())

    def test_existing_result_is_not_overwritten(self):
        self.output.write_text("existing", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.run_pipeline()
        self.assertEqual(self.output.read_text(encoding="utf-8"), "existing")
        self.assertEqual(self.requests, [])


if __name__ == "__main__":
    unittest.main()
