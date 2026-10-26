"""Перевірки extract без мережі та провайдерського SDK."""

import copy
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from main import DevicePosting, RESPONSE_FORMAT, extract


EXPECTED = {
    "language": "uk",
    "primary_topic": "sensors_measurements",
    "mentioned_platforms": ["arduino"],
    "mentioned_interfaces": ["i2c"],
    "mentions_sensor": True,
    "mentions_display": False,
    "mentions_battery": False,
    "mentions_motor": False,
}


def response(content=None, *, finish_reason="stop", refusal=None, usage=True):
    message = SimpleNamespace(content=content, refusal=refusal)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason=finish_reason)],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5) if usage else None,
    )


class ExtractTests(unittest.TestCase):
    def setUp(self):
        self.messages = [
            {"role": "system", "content": "Витягни дані за Schema v2."},
            {"role": "user", "content": "Датчик Arduino підключено через I2C."},
        ]
        self.text = self.messages[-1]["content"]

    def run_extract(self, *responses):
        client = Mock()
        client.chat.completions.create.side_effect = list(responses)
        return extract(client, self.messages, self.text, "test-model"), client

    def test_success_sends_schema_and_passes_context(self):
        original = copy.deepcopy(self.messages)
        with patch.object(DevicePosting, "model_validate_json",
                          wraps=DevicePosting.model_validate_json) as validate:
            result, client = self.run_extract(response(json.dumps(EXPECTED)))
        self.assertTrue(result["ok"])
        self.assertTrue(result["first_attempt_valid"])
        self.assertFalse(result["repair_attempted"])
        self.assertEqual(result["data"], EXPECTED)
        self.assertEqual(result["attempts"], 1)
        self.assertEqual((result["input_tokens"], result["output_tokens"]), (10, 5))
        self.assertIsNone(result["error"])
        self.assertGreaterEqual(result["seconds"], result["first_attempt_seconds"])
        validate.assert_called_once_with(json.dumps(EXPECTED), strict=True,
                                         context={"text": self.text})
        client.chat.completions.create.assert_called_once_with(
            model="test-model", messages=self.messages, response_format=RESPONSE_FORMAT,
        )
        self.assertEqual(self.messages, original)

    def test_one_repair_preserves_first_response_and_usage(self):
        original = copy.deepcopy(self.messages)
        for invalid in ("not json", "{}", json.dumps(dict(EXPECTED, mentions_sensor="true"))):
            with self.subTest(invalid=invalid):
                result, client = self.run_extract(
                    response(invalid), response(json.dumps(EXPECTED)),
                )
                self.assertTrue(result["ok"])
                self.assertFalse(result["first_attempt_valid"])
                self.assertTrue(result["repair_attempted"])
                self.assertEqual(result["attempts"], 2)
                self.assertEqual((result["input_tokens"], result["output_tokens"]), (20, 10))
                self.assertEqual(result["responses"][0]["content"], invalid)
                self.assertIsNotNone(result["responses"][0]["error"])
                self.assertIsNone(result["error"])
                repair = client.chat.completions.create.call_args_list[1].kwargs["messages"]
                self.assertEqual(repair[:2], self.messages)
                self.assertEqual(repair[2], {"role": "assistant", "content": invalid})
                self.assertIn(result["responses"][0]["error"], repair[3]["content"])
                self.assertEqual(self.messages, original)

    def test_second_invalid_response_fails_without_third_call(self):
        result, client = self.run_extract(response("{}"), response("{}"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["data"])
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(client.chat.completions.create.call_count, 2)
        self.assertTrue(all(record["error"] for record in result["responses"]))

    def test_terminal_responses_are_not_repaired(self):
        cases = [
            response(json.dumps(EXPECTED), refusal="Відмова"),
            response(json.dumps(EXPECTED), finish_reason="length"),
            response(json.dumps(EXPECTED), finish_reason="content_filter"),
            response(json.dumps(EXPECTED), finish_reason="tool_calls"),
            response(None), response("   "),
            SimpleNamespace(choices=[], usage=None),
        ]
        for item in cases:
            with self.subTest(item=item):
                result, client = self.run_extract(item)
                self.assertFalse(result["ok"])
                self.assertFalse(result["repair_attempted"])
                self.assertEqual(result["attempts"], 1)
                self.assertIsNotNone(result["error"])
                client.chat.completions.create.assert_called_once()

    def test_transport_error_is_not_a_repair(self):
        result, client = self.run_extract(TimeoutError("timeout"))
        self.assertFalse(result["ok"])
        self.assertFalse(result["repair_attempted"])
        self.assertIn("TimeoutError", result["error"])
        self.assertIsNone(result["input_tokens"])
        client.chat.completions.create.assert_called_once()

    def test_transport_error_during_repair_preserves_first_attempt(self):
        result, client = self.run_extract(response("{}"), TimeoutError("timeout"))
        self.assertFalse(result["ok"])
        self.assertTrue(result["repair_attempted"])
        self.assertEqual(len(result["responses"]), 2)
        self.assertEqual(result["responses"][0]["content"], "{}")
        self.assertIn("TimeoutError", result["responses"][1]["error"])
        self.assertIsNone(result["input_tokens"])
        self.assertEqual(client.chat.completions.create.call_count, 2)

    def test_missing_usage_is_unknown_not_zero(self):
        result, _ = self.run_extract(response(json.dumps(EXPECTED), usage=False))
        self.assertTrue(result["ok"])
        self.assertIsNone(result["input_tokens"])
        self.assertIsNone(result["output_tokens"])


if __name__ == "__main__":
    unittest.main()
