"""Канонічні enum, унікальність, repair і контроль ідентичності контракту."""

import json
import unittest
from typing import get_args
from unittest.mock import Mock

from pydantic import ValidationError

import main
from schema_contracts import (CONTRACT_VERSION, CONTRACT_SHA256, LEGACY_CONTRACT_VERSION,
                              DevicePosting, LegacyDevicePosting, HardwarePlatform, Interface,
                              contract_descriptor, contract_hash, record_contract)
from test_extract import EXPECTED, response


class StrictSchemaTests(unittest.TestCase):
    def test_every_canonical_tag_and_empty_lists_are_allowed(self):
        for platforms, interfaces in ((list(get_args(HardwarePlatform)), list(get_args(Interface))), ([], [])):
            payload = dict(EXPECTED, mentioned_platforms=platforms, mentioned_interfaces=interfaces)
            self.assertEqual(DevicePosting.model_validate(payload).model_dump(), payload)

    def test_unknown_noncanonical_and_duplicate_values_are_rejected(self):
        for field, invalid in (
            ("mentioned_platforms", ["Telegram"]), ("mentioned_platforms", ["Arduino UNO"]),
            ("mentioned_platforms", ["Arduino"]), ("mentioned_interfaces", ["WiFi"]),
            ("mentioned_interfaces", ["USB"]), ("mentioned_interfaces", ["relay pin"]),
            ("mentioned_interfaces", [" wifi "]), ("mentioned_platforms", ["arduino", "arduino"]),
            ("mentioned_interfaces", ["usb", "usb"]),
        ):
            with self.subTest(field=field, invalid=invalid), self.assertRaises(ValidationError):
                DevicePosting.model_validate(dict(EXPECTED, **{field: invalid}))

    def test_fields_required_extra_null_and_coercion_are_rejected(self):
        for field in EXPECTED:
            missing = dict(EXPECTED)
            missing.pop(field)
            for payload in (missing, dict(EXPECTED, **{field: None})):
                with self.subTest(field=field), self.assertRaises(ValidationError):
                    DevicePosting.model_validate(payload)
        for payload in (dict(EXPECTED, extra="unexpected"), dict(EXPECTED, mentions_sensor="true"),
                        dict(EXPECTED, mentions_sensor=1), dict(EXPECTED, mentioned_platforms="arduino")):
            with self.assertRaises(ValidationError):
                DevicePosting.model_validate(payload)

    def test_wire_schema_has_enums_required_fields_and_no_unique_items(self):
        schema = DevicePosting.model_json_schema()
        self.assertEqual(set(schema["required"]), set(EXPECTED))
        self.assertIs(schema["additionalProperties"], False)
        self.assertEqual(schema["properties"]["mentioned_platforms"]["items"]["enum"], list(get_args(HardwarePlatform)))
        self.assertEqual(schema["properties"]["mentioned_interfaces"]["items"]["enum"], list(get_args(Interface)))
        self.assertNotIn("uniqueItems", json.dumps(schema))
        self.assertEqual(main.RESPONSE_FORMAT["json_schema"]["schema"], schema)

    def test_enum_or_duplicate_errors_use_one_repair_without_rewriting_raw(self):
        for invalid in (["Telegram"], ["arduino", "arduino"]):
            with self.subTest(invalid=invalid):
                payload = dict(EXPECTED, mentioned_platforms=invalid)
                original = json.dumps(payload)
                client = Mock()
                first, repaired = response(original), response(json.dumps(EXPECTED))
                first.model = repaired.model = "returned-snapshot"
                client.chat.completions.create.side_effect = [first, repaired]
                result = main.extract(client, [{"role": "user", "content": "Article"}], "Article", "requested-alias")
                self.assertTrue(result["ok"])
                self.assertFalse(result["first_attempt_valid"])
                self.assertEqual(result["first_attempt_status"], "invalid")
                self.assertEqual(result["actual_model"], "returned-snapshot")
                self.assertEqual(result["responses"][0]["content"], original)
                self.assertIn("mentioned_platforms", result["responses"][0]["error"])
                self.assertTrue(result["repair_attempted"])
                self.assertEqual(result["attempts"], 2)

    def test_second_duplicate_response_is_failed_and_secret_errors_are_not_logged(self):
        raw = json.dumps(dict(EXPECTED, mentioned_interfaces=["usb", "usb"]))
        client = Mock()
        client.chat.completions.create.side_effect = [response(raw), response(raw)]
        result = main.extract(client, [], "Article", "test")
        self.assertFalse(result["ok"])
        self.assertEqual(result["attempts"], 2)
        self.assertEqual([item["content"] for item in result["responses"]], [raw, raw])
        client.chat.completions.create.side_effect = RuntimeError("private-secret-key")
        failed = main.extract(client, [], "Article", "test")
        self.assertNotIn("private-secret-key", json.dumps(failed))
        self.assertEqual(failed["first_attempt_status"], "api_error")
        first = response(raw)
        first.model = "returned-before-repair-error"
        client.chat.completions.create.side_effect = [first, RuntimeError("private-secret-key")]
        failed = main.extract(client, [], "Article", "test")
        self.assertFalse(failed["ok"])
        self.assertEqual(failed["actual_model"], "returned-before-repair-error")
        self.assertNotIn("private-secret-key", json.dumps(failed))

    def test_hash_includes_local_rules_and_rejects_unknown_or_partial_contracts(self):
        self.assertEqual(CONTRACT_SHA256, contract_hash(CONTRACT_VERSION))
        self.assertNotEqual(CONTRACT_SHA256, contract_hash(LEGACY_CONTRACT_VERSION))
        self.assertEqual(contract_descriptor(CONTRACT_VERSION)["unique_list_fields"], ["mentioned_platforms", "mentioned_interfaces"])
        self.assertEqual(record_contract({"schema_version": "v2"}), LEGACY_CONTRACT_VERSION)
        for metadata in ({"contract_version": CONTRACT_VERSION}, {"contract_sha256": CONTRACT_SHA256},
                         {"contract_version": "unknown", "contract_sha256": CONTRACT_SHA256},
                         {"contract_version": CONTRACT_VERSION, "contract_sha256": "wrong"}):
            with self.assertRaises(ValueError):
                record_contract(dict(schema_version="v2", **metadata))

    def test_legacy_keeps_original_string_and_duplicate_semantics(self):
        data = dict(EXPECTED, mentioned_platforms=["Telegram", "Telegram"], mentioned_interfaces=["Wi-Fi"])
        self.assertEqual(LegacyDevicePosting.model_validate(data, strict=True).model_dump(), data)


if __name__ == "__main__":
    unittest.main()
