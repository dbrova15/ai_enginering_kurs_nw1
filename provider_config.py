"""Чиста спільна конфігурація провайдера; жодних API-викликів при імпорті."""

import os


def get_provider() -> str:
    """Нормалізує LLM_PROVIDER і перевіряє підтримуваний ідентифікатор.

    Читає вже підготовлене оточення; load_dotenv виконує entry point.
    Невідомий provider відхиляється до мережі. Типова поведінка ДЗ1
    збережена: openrouter, якщо змінну не задано.
    """
    provider = os.getenv("LLM_PROVIDER", "openrouter").strip().lower()
    if provider not in ("openai", "openrouter", "ollama"):
        raise ValueError(f"Невідомий LLM_PROVIDER: {provider}")
    return provider


def load_model() -> tuple[str, str, str]:
    """Повертає (base_url, api_key, model), зберігаючи правила старого CLI.

    Для OpenAI/OpenRouter вимагає ключ; для Ollama використовує службове
    значення й нормалізує /v1. Не перевіряє endpoint і не журналює
    секрет: повернений api_key можна передати тільки API-клієнту.
    """
    provider = get_provider()
    if provider == "openrouter":
        base_url = "https://openrouter.ai/api/v1"
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        model = os.getenv("OPENROUTER_MODEL", "").strip() or "openai/gpt-4o-mini"
    elif provider == "openai":
        base_url = "https://api.openai.com/v1"
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "").strip() or "gpt-4o-mini"
    else:
        server = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip().rstrip("/")
        base_url = server if server.endswith("/v1") else server + "/v1"
        api_key = "ollama"
        model = os.getenv("OLLAMA_MODEL", "").strip() or "llama3.2:3b"
    if not api_key:
        raise ValueError(f"Не задано API-ключ для {provider}")
    return base_url, api_key, model
