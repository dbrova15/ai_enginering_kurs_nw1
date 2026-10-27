"""Два явні контракти Schema v2: історичний strings і новий enums/unique."""

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

HardwarePlatform = Literal["arduino", "esp32", "esp8266", "stm32", "raspberry_pi", "orange_pi"]
Interface = Literal["wifi", "bluetooth", "lora", "i2c", "spi", "uart", "usb"]
LEGACY_CONTRACT_VERSION = "schema-v2-strings-1"
CONTRACT_VERSION = "schema-v2-enums-1"


# Без docstring: Pydantic інакше додасть description до історичної wire-схеми.
class LegacyDevicePosting(BaseModel):
    model_config = ConfigDict(extra="forbid", title="DevicePosting")
    language: Literal["en", "ru", "uk"]
    primary_topic: Literal[
        "devices_automation", "controllers_programming", "robotics_actuators",
        "sensors_measurements", "displays_indicators", "communications_iot",
        "power_batteries", "printing_mechanics",
    ]
    mentioned_platforms: list[str]
    mentioned_interfaces: list[str]
    mentions_sensor: bool
    mentions_display: bool
    mentions_battery: bool
    mentions_motor: bool


class DevicePosting(LegacyDevicePosting):
    """Чинний контракт: канонічні теги, строгі типи та унікальні списки."""

    model_config = ConfigDict(extra="forbid", title="DevicePosting", strict=True)
    mentioned_platforms: list[HardwarePlatform]
    mentioned_interfaces: list[Interface]

    @field_validator("mentioned_platforms", "mentioned_interfaces")
    @classmethod
    def require_unique(cls, values: list) -> list:
        """Відхиляє повтори, не змінюючи відповідь моделі перед repair."""
        if len(values) != len(set(values)):
            raise ValueError("Кожен тег може бути зазначений лише один раз")
        return values


def contract_descriptor(version: str) -> dict:
    """Описує wire-схему та локальні правила, які також є частиною контракту."""
    if version not in (LEGACY_CONTRACT_VERSION, CONTRACT_VERSION):
        raise ValueError(f"Невідомий контракт: {version}")
    model = LegacyDevicePosting if version == LEGACY_CONTRACT_VERSION else DevicePosting
    return {"version": version, "json_schema": model.model_json_schema(),
            "strict_validation": True,
            "unique_list_fields": ["mentioned_platforms", "mentioned_interfaces"] if version == CONTRACT_VERSION else []}


def contract_hash(version: str) -> str:
    """Рахує SHA-256 детермінованого опису, включно з локальною унікальністю."""
    content = json.dumps(contract_descriptor(version), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


CONTRACT_SHA256 = contract_hash(CONTRACT_VERSION)
LEGACY_CONTRACT_SHA256 = contract_hash(LEGACY_CONTRACT_VERSION)


def record_contract(record: dict, *, require_envelope: bool = True) -> str:
    """Визначає контракт запису; тільки старі v2 без обох полів є legacy.

    Частково задані, невідомі або підмінені version/hash завжди є помилкою.
    Новий запис також повинен мати явного провайдера й запитану модель.
    """
    if record.get("schema_version") != "v2":
        raise ValueError("Підтримується лише Schema v2")
    if "contract_version" not in record and "contract_sha256" not in record:
        return LEGACY_CONTRACT_VERSION
    version = record.get("contract_version")
    if version not in (LEGACY_CONTRACT_VERSION, CONTRACT_VERSION):
        raise ValueError(f"Невідомий контракт: {version}")
    if record.get("contract_sha256") != contract_hash(version):
        raise ValueError(f"Неправильний contract_sha256 для {version}")
    if version == CONTRACT_VERSION:
        if record.get("provider") not in ("openai", "openrouter", "ollama"):
            raise ValueError("Новий контракт вимагає відомого provider")
        requested = record.get("requested_model")
        if not isinstance(requested, str) or not requested.strip() or requested != record.get("model"):
            raise ValueError("requested_model має відповідати model")
        if require_envelope and ("actual_model" not in record or (record["actual_model"] is not None and not isinstance(record["actual_model"], str))):
            raise ValueError("actual_model має бути рядком або null, якщо API його не повернув")
    return version


def model_for_contract(version: str):
    """Повертає саме ту модель валідації, за якою генерувався відповідний запис."""
    contract_descriptor(version)
    return LegacyDevicePosting if version == LEGACY_CONTRACT_VERSION else DevicePosting


def single_contract(records: list[dict], *, require_envelope: bool = True) -> str:
    """Забороняє спільне порівняння різних контрактів, навіть за однакової v2."""
    versions = {record_contract(record, require_envelope=require_envelope) for record in records}
    if len(versions) != 1:
        raise ValueError("Змішані контракти: оберіть один через --contract або окремі файли")
    return versions.pop()


def report_contract(report: dict, *, historical: bool) -> str:
    """Читає контракт нового звіту; для старої версії звіту дозволений лише legacy."""
    if historical:
        if "contract_version" in report or "contract_sha256" in report:
            raise ValueError("Історичний формат звіту не може декларувати новий контракт")
        return LEGACY_CONTRACT_VERSION
    version = report.get("contract_version")
    if report.get("contract_sha256") != contract_hash(version):
        raise ValueError("Контракт звіту має неправильний SHA-256")
    return version
