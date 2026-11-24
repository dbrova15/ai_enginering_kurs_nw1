"""Локальний tiktoken profile із явною підготовкою й hash-перевіркою cache."""

import os
from pathlib import Path
from ..artifacts import file_digest, read_json, write_json


def prepare_encoding(assets: Path) -> dict:
    """Явно отримує o200k_base tokenizer під час дозволеного bootstrap.

    Це файл токенізації, не LLM і не платний API-запит. Фіксує cache
    hashes; наступні ask/eval відмовляються працювати без цих файлів.
    """
    import tiktoken
    directory = assets / "llm-tokenizer"
    directory.mkdir(parents=True, exist_ok=True)
    os.environ["TIKTOKEN_CACHE_DIR"] = str(directory.resolve())
    tiktoken.get_encoding("o200k_base")
    files = {p.name: file_digest(p) for p in directory.iterdir() if p.is_file()}
    metadata = {"encoding": "o200k_base", "files": files}
    if not files:
        raise ValueError("Tokenizer cache порожній; виконайте bootstrap в окремому процесі")
    write_json(assets / "llm-tokenizer.json", metadata)
    return metadata


class LlmTokens:
    """Токенізатор перевіреного OpenAI-профілю без мережі при ask.

    Підтримує тільки явно підготовлений o200k_base. Іншу модель не
    можна мовчки вимірювати чужим tokenizer: потрібен новий profile.
    """
    def __init__(self, assets: Path, encoding: str):
        """Перевіряє cache hashes до виклику tiktoken.get_encoding.

        Правильні cached bytes дозволяють бібліотеці читати локально;
        відсутній/зіпсований файл зупиняє роботу до можливого download.
        """
        import tiktoken
        metadata = read_json(assets / "llm-tokenizer.json")
        if encoding != "o200k_base" or metadata["encoding"] != encoding or not metadata["files"]:
            raise ValueError("Непідтримуваний tokenizer profile")
        directory = assets / "llm-tokenizer"
        for name, expected in metadata["files"].items():
            path = directory / name
            if not path.resolve().is_relative_to(directory.resolve()) or file_digest(path) != expected:
                raise ValueError("LLM tokenizer cache несумісний")
        os.environ["TIKTOKEN_CACHE_DIR"] = str(directory.resolve())
        self.encoding = tiktoken.get_encoding(encoding)

    def count(self, text: str) -> int:
        """Повертає exact count тексту, трактуючи special strings як дані.

        Запобігає помилці чи змішуванню ролей через текст на кшталт
        special-token marker усередині недовіреного документа.
        """
        return len(self.encoding.encode(text, disallowed_special=()))
