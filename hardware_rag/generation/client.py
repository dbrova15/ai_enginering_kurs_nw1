"""Прозорий provider adapter: timeout/retry, raw attempts, usage та per-run cap."""

import os
import time
from ..answers import Attempt
from ..artifacts import canonical_json
from .context import TOKEN_MARGIN
from provider_config import get_provider, load_model


class LlmClient:
    """Виконує строго обмежені OpenAI-compatible виклики й журналює спроби.

    Платний профіль потребує enabled, тарифної дати й Budget. Caller
    може передати fake transport для офлайн-тесту; на реальну якість
    відповіді ці тести не претендують.
    """
    def __init__(self, config, tokens, budget, *, judge: bool = False, transport=None, sleeper=time.sleep):
        """Вибирає окрему RAG/JUDGE model і вимикає приховані SDK retries.

        Підтримуваний початковий tokenizer profile — gpt-4o-mini.
        Ollama потребує окремого перевіреного profile й не підміняється
        вимірюванням OpenAI tokenizer. Секрет зберігається тільки в SDK.
        """
        from openai import OpenAI
        provider = get_provider()
        if provider == "ollama":
            raise ValueError("model_profile_unverified: для RAG/Ollama потрібен точний локальний tokenizer profile")
        if provider != "ollama" and (not config.paid_enabled or budget is None or not config.pricing_date):
            raise ValueError("paid_disabled: потрібні окремий бюджет і тарифна дата")
        if provider != "ollama" and (config.pricing_provider != provider or not config.price_source):
            raise ValueError("pricing_profile_mismatch: тариф має відповідати активному провайдеру")
        base_url, key, fallback = load_model()
        self.model = os.getenv("RAG_JUDGE_MODEL" if judge else "RAG_MODEL", "").strip() or fallback
        if self.model not in ("gpt-4o-mini", "openai/gpt-4o-mini"):
            raise ValueError("model_profile_unverified: потрібен підтверджений tokenizer/schema profile")
        self.provider, self.config, self.tokens, self.budget = provider, config, tokens, budget
        self.transport = transport or OpenAI(base_url=base_url, api_key=key, timeout=config.timeout_seconds, max_retries=0)
        self.sleeper = sleeper
        self.attempts = []

    def call(self, messages: list[dict], schema: dict, *, kind: str = "primary") -> str:
        """Повертає завершений JSON-текст або безпечну технічну помилку.

        До кожної transport-спроби резервує worst-case model input/output.
        Retry дозволено тільки для timeout/429/5xx; refusal/обрив не
        маскуються repair. Кожний отриманий response зберігає usage.
        """
        from openai import APIConnectionError, APITimeoutError
        payload = {"messages": messages, "response_format": schema}
        if self.tokens.count(canonical_json(payload)) + TOKEN_MARGIN + self.config.output_tokens > self.config.model_context_tokens:
            raise ValueError("context_overflow: запит не виконано")
        for retry in range(self.config.transport_retries + 1):
            reserved = self.budget.reserve(self.config.model_context_tokens, self.config.output_tokens)
            started = time.perf_counter()
            attempt_kind = "retry" if retry else kind
            try:
                response = self.transport.chat.completions.create(model=self.model, messages=messages,
                    response_format=schema, temperature=0, max_tokens=self.config.output_tokens)
            except Exception as error:
                status = getattr(error, "status_code", None)
                self.budget.settle(reserved, None, None)
                self.attempts.append(Attempt(kind=attempt_kind, status="transport_error",
                    seconds=time.perf_counter() - started, error=f"{type(error).__name__}; HTTP={status}"))
                transient = isinstance(error, (APIConnectionError, APITimeoutError)) or status == 429 or (isinstance(status, int) and status >= 500)
                if transient and retry < self.config.transport_retries:
                    self.sleeper(min(2 ** retry, 4))
                    continue
                raise ValueError("provider_error: подробиці без секретів у attempts") from None
            usage = response.usage
            choice = response.choices[0] if response.choices else None
            message = choice.message if choice else None
            content = message.content if message else None
            input_tokens = usage.prompt_tokens if usage else None
            output_tokens = usage.completion_tokens if usage else None
            status = "received"
            if message is None or choice.finish_reason != "stop":
                status = "incomplete"
            if getattr(message, "refusal", None):
                status = "refused"
            self.attempts.append(Attempt(kind=attempt_kind, status=status, content=content,
                actual_model=getattr(response, "model", None), input_tokens=input_tokens,
                output_tokens=output_tokens, finish_reason=choice.finish_reason if choice else None,
                seconds=time.perf_counter() - started))
            self.budget.settle(reserved, input_tokens, output_tokens)
            if status != "received" or not content:
                raise ValueError(f"provider_{status}")
            return content
        raise ValueError("retry_limit_exhausted")
