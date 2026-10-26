
import argparse
import hashlib
import os
import re
from pathlib import Path
import json
import time
from datetime import datetime, timezone
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, ValidationError

ROOT = Path(__file__).resolve().parent

load_dotenv(ROOT / ".env")
# Допустимі значення: openrouter, openai, ollama; типово openrouter
LLM_PROVIDER = "openai"   # os.getenv("LLM_PROVIDER", "openrouter").strip().lower()
PROMPTS = ROOT / "prompts"
GOLDEN = ROOT / "data" / "sourses" / "hm1" / "golden.json"
TEXTS = GOLDEN.parent / "texts"
RESULTS = ROOT / "results"
SCHEMA_VERSION = "v2"
PREPARATION_VERSION = "schema-v2-initial-metadata-v1"

def get_text_files() -> list[Path]:
    return [
        path
        for language in ("en", "ru", "uk")
        for path in sorted((TEXTS / language).iterdir())
        if path.is_file() and path.suffix.lower() == ".txt"
    ]

def get_text_from_file(file_paths: list[Path] | None = None) -> list[str]:
    """Збирає тексти з англійської, російської та української вибірок."""
    paths = get_text_files() if file_paths is None else file_paths
    return [path.read_bytes().decode("utf-8") for path in paths]


def prepare_text(text: str) -> str:
    """Видаляє лише повний початковий блок метаданих, зберігаючи заголовок."""
    lines = text.splitlines(keepends=True)
    start = 0 if lines and lines[0].startswith("Автори:") else 1
    index = start
    for label in ("Автори:", "Категорії:", "Плати:"):
        while index < len(lines) and not lines[index].strip():
            index += 1
        if index >= len(lines) or not lines[index].startswith(label):
            return text
        index += 1
    return "".join(lines[:start] + lines[index:])

class DevicePosting(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: Literal["en", "ru", "uk"]
    primary_topic: Literal[
        "devices_automation",
        "controllers_programming",
        "robotics_actuators",
        "sensors_measurements",
        "displays_indicators",
        "communications_iot",
        "power_batteries",
        "printing_mechanics",
    ]
    mentioned_platforms: list[str]
    mentioned_interfaces: list[str]
    mentions_sensor: bool
    mentions_display: bool
    mentions_battery: bool
    mentions_motor: bool

RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "DevicePosting",
        "strict": True,
        "schema": DevicePosting.model_json_schema(),
    },
}
MAX_EXTRACTION_ATTEMPTS = 2


def _response_record(response, seconds: float) -> dict:
    choice = response.choices[0] if response.choices else None
    message = choice.message if choice else None
    usage = response.usage
    return {
        "content": message.content if message else None,
        "refusal": getattr(message, "refusal", None),
        "finish_reason": choice.finish_reason if choice else None,
        "input_tokens": usage.prompt_tokens if usage else None,
        "output_tokens": usage.completion_tokens if usage else None,
        "seconds": seconds,
        "error": None,
    }


def _validate_extraction_response(record: dict, text: str) -> DevicePosting:
    if record["refusal"]:
        raise ValueError(f"Модель відмовилася: {record['refusal']}")
    if record["finish_reason"] != "stop":
        raise ValueError(f"Відповідь не завершена: {record['finish_reason']}")
    content = record["content"]
    if not content or not content.strip():
        raise ValueError("Порожня відповідь моделі")
    return DevicePosting.model_validate_json(content, strict=True, context={"text": text})


def extract(client: OpenAI, messages: list[dict], text: str, model: str,
            *, sampling: dict | None = None) -> dict:
    """Валідує Schema v2; після помилки JSON/Pydantic дозволяє один repair.

    messages має містити промпт і текст статті; text передається у context
    валідації. Сам context без спеціальних валідаторів не перевіряє факти.
    Мережевими retry керує клієнт; attempts рахує виклики create разом із repair.
    """
    start = time.perf_counter()
    result = {
        "ok": False, "status": "failed", "attempts": 0, "data": None,
        "first_attempt_valid": False, "repair_attempted": False,
        "responses": [], "error": None,
    }
    repair_messages = list(messages)
    for attempt in range(MAX_EXTRACTION_ATTEMPTS):
        result["attempts"] += 1
        result["repair_attempted"] = attempt > 0
        attempt_start = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=model, messages=repair_messages,
                response_format=RESPONSE_FORMAT,
                **(sampling or {}),
            )
        except Exception as error:
            result["error"] = f"{type(error).__name__}: {error}"
            result["responses"].append({
                "content": None, "input_tokens": None, "output_tokens": None,
                "seconds": time.perf_counter() - attempt_start,
                "error": result["error"],
            })
            break
        record = _response_record(response, time.perf_counter() - attempt_start)
        result["responses"].append(record)
        try:
            posting = _validate_extraction_response(record, text)
        except ValidationError as error:
            record["error"] = str(error)
            if attempt + 1 < MAX_EXTRACTION_ATTEMPTS:
                repair_messages = repair_messages + [
                    {"role": "assistant", "content": record["content"]},
                    {"role": "user", "content": (
                        "Виправ JSON за схемою, спираючись лише на вихідну статтю. "
                        "Поверни лише JSON. Помилки валідації:\n" + str(error)
                    )},
                ]
                continue
        except ValueError as error:
            record["error"] = str(error)
        else:
            result.update(ok=True, status="success", data=posting.model_dump(),
                          first_attempt_valid=attempt == 0)
        result["error"] = record["error"]
        break
    for field in ("input_tokens", "output_tokens"):
        values = [record[field] for record in result["responses"]]
        result[field] = sum(values) if all(value is not None for value in values) else None
    result["first_attempt_seconds"] = result["responses"][0]["seconds"]
    result["seconds"] = time.perf_counter() - start
    return result


def load_model() -> tuple[str, str, str]:
    if LLM_PROVIDER == "openrouter":
        base_url = "https://openrouter.ai/api/v1"
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        model = os.getenv("OPENROUTER_MODEL", "").strip() or "openai/gpt-4o-mini"
    elif LLM_PROVIDER == "openai":
        base_url = "https://api.openai.com/v1"
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "").strip() or "gpt-4o-mini"
    elif LLM_PROVIDER == "ollama":
        server = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip().rstrip("/")
        base_url = server if server.endswith("/v1") else server + "/v1"
        api_key = "ollama"
        model = os.getenv("OLLAMA_MODEL", "").strip() or "llama3.2:3b"
    else:
        raise ValueError(f"Невідомий LLM_PROVIDER: {LLM_PROVIDER}")
    if not api_key:
        raise ValueError(f"Не задано API-ключ для {LLM_PROVIDER}")
    return base_url, api_key, model

def load_prompt(version: str) -> tuple[str, str]:
    if version == "v1":
        prompt = (PROMPTS / "v1.txt").read_text(encoding="utf-8")
    elif version == "v2":
        prompt = (PROMPTS / "v2.txt").read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported prompt version: {version}")

    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    return prompt, prompt_hash

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Витягування даних із технічних статей")
    parser.add_argument("prompt_version", nargs="?", choices=("v1", "v2"), default="v1")
    parser.add_argument("--limit", type=int, help="Обробити лише перші N статей")
    parser.add_argument("--output", type=Path, help="Новий JSONL-файл результатів")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit має бути додатним")
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    base_url, api_key, model = load_model()
    system, prompt_hash = load_prompt(args.prompt_version)
    paths = get_text_files()

    if args.limit is not None:
        paths = paths[:args.limit]
    if not paths:
        raise ValueError("Не знайдено жодної TXT-статті")
    texts = get_text_from_file(paths)
    sampling = {
        "temperature": float(os.getenv("TEMPERATURE", "0")),
        "top_p": float(os.getenv("TOP_P", "1")),
    }
    max_tokens = os.getenv("MAX_TOKENS", "").strip()
    if max_tokens:
        sampling["max_tokens"] = int(max_tokens)
        if sampling["max_tokens"] < 1:
            raise ValueError("MAX_TOKENS має бути додатним цілим числом")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    model_name = re.sub(r"[^A-Za-z0-9._-]+", "_", model).strip("._") or "model"
    output = args.output or RESULTS / f"prompt_{args.prompt_version}_{model_name}_{timestamp}.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    valid = 0
    with output.open("x", encoding="utf-8") as destination, OpenAI(
        base_url=base_url, api_key=api_key,
        timeout=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "60")),
        max_retries=int(os.getenv("MAX_RETRIES", "2")),
    ) as client:
        for path, original in zip(paths, texts, strict=True):
            text = prepare_text(original)
            messages = [{"role": "system", "content": system},
                        {"role": "user", "content": text}]
            result = extract(client, messages, text, model, sampling=sampling)
            record = {
                "document_id": path.stem, "source_path": str(path),
                "schema_version": SCHEMA_VERSION, "model": model,
                "prompt_version": args.prompt_version, "prompt_sha256": prompt_hash,
                "sampling": sampling, "timestamp": datetime.now(timezone.utc).isoformat(),
                "source_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
                "preparation_version": PREPARATION_VERSION,
                "input_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "result": result,
            }
            destination.write(json.dumps(record, ensure_ascii=False) + "\n")
            destination.flush()
            valid += int(result["ok"])
            print(f"{path.stem}: {result['status']}")
    print(f"Валідних: {valid}/{len(paths)}. Результати: {output}")




if __name__ == "__main__":
    main()
