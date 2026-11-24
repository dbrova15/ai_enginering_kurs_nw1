"""Детерміновані hashes та атомарний запис нових артефактів ДЗ2."""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def canonical_json(value: Any) -> str:
    """Повертає стабільний JSON, незалежний від порядку ключів словника.

    Зберігає Unicode, забороняє NaN; призначений для fingerprints.
    Час запуску слід вилучити до виклику, якщо він не є частиною input.
    """
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    """Обчислює SHA-256 канонічного JSON для config/dataset/контракту.

    Не використовувати для байтів оригіналу: їх окремо обробляє
    file_digest, щоб не змішувати сирі й нормалізовані представлення.
    """
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    """Читає файл блоками й повертає SHA-256 незмінених сирих байтів.

    Придатна для великих ваг моделей; не декодує текст. Відсутність
    файла спричиняє помилку, а не повернення вигаданого хешу.
    """
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def text_digest(text: str) -> str:
    """Обчислює SHA-256 саме UTF-8 тексту, фактично переданого моделі.

    На відміну від digest не додає JSON-лапки й escaping. Потрібна
    для prompt/input hashes, щоб відтворення не плутало файл і JSON value.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any:
    """Читає UTF-8 JSON без fallback на порожній об'єкт при помилці.

    Типи та інваріанти отриманих даних перевіряє відповідний контракт;
    ця функція відповідає тільки за коректне декодування файла.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any, *, replace: bool = False) -> None:
    """Публікує JSON атомарно; immutable-артефакт не можна перезаписати.

    replace=True призначено для current pointer. Тимчасовий файл у
    тому самому каталозі забезпечує атомарність; помилка прибирає лише
    цей тимчасовий файл і не видаляє попередній результат користувача.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not replace:
        raise FileExistsError(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(canonical_json(value) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def within(root: Path, relative: str) -> Path:
    """Дозволяє файловий шлях лише всередині resolved workspace.

    Враховує ../ та наявні symlink. Використовується для paths із
    конфігурації/реєстру, ніколи не для мережевих URL.
    """
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError("Шлях виходить за межі workspace")
    return target
