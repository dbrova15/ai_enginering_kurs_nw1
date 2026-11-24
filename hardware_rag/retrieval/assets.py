"""Явне отримання й перевірка локальних ONNX assets без API-генерацій."""

from pathlib import Path
from ..artifacts import file_digest, read_json, write_json

# Репозиторії та файли зафіксованих у дизайні моделей, не довільний remote code.
MODEL_SPECS = {
    "embedding": {"repo": "intfloat/multilingual-e5-small", "file": "onnx/model.onnx",
                  "model": "intfloat/multilingual-e5-small"},
    "reranker": {"repo": "onnx-community/bge-reranker-v2-m3-ONNX", "file": "onnx/model_int8.onnx",
                 "model": "BAAI/bge-reranker-v2-m3-int8"},
}
# Tokenizer/config потрібні для exact counts і відтворення preprocessing моделі.
TOKENIZER_FILES = ["tokenizer.json", "tokenizer_config.json", "special_tokens_map.json",
                   "config.json", "sentencepiece.bpe.model"]


def prepare_assets(directory: Path, *, download: bool = False) -> dict:
    """Завантажує погоджені assets тільки за явного download=True.

    Фіксує точну HF revision, SHA-256 кожного файла та model IDs.
    Повторний звичайний виклик тільки перевіряє вже зафіксовані файли;
    не оновлює їх до нового main і не отримує інші ваги автоматично.
    """
    if (directory / "assets.json").exists():
        return verify_assets(directory)
    if not download:
        raise ValueError("assets_missing: виконайте prepare-models --download після дозволу")
    from huggingface_hub import HfApi, snapshot_download
    lock_path = Path(__file__).resolve().parents[2] / "config/hw2-models.json"
    lock = read_json(lock_path) if lock_path.exists() else None
    result = {}
    for role, spec in MODEL_SPECS.items():
        revision = lock[role]["revision"] if lock else HfApi().model_info(spec["repo"]).sha
        local = directory / role
        snapshot_download(spec["repo"], revision=revision, local_dir=local,
                          allow_patterns=TOKENIZER_FILES + [spec["file"]])
        required = [local / "tokenizer.json", local / spec["file"]]
        if not all(path.is_file() for path in required):
            raise ValueError(f"Неповні assets для {role}")
        files = {p.relative_to(directory).as_posix(): file_digest(p)
                 for p in local.rglob("*") if p.is_file() and ".cache" not in p.parts}
        if lock and files != lock[role]["files"]:
            raise ValueError("assets_incompatible: отримані байти не відповідають approved lock")
        result[role] = {**spec, "revision": revision, "files": files}
    write_json(directory / "assets.json", result)
    return result


def verify_assets(directory: Path) -> dict:
    """Перевіряє повний зафіксований набір ваг/токенізаторів без мережі.

    Повертає metadata тільки після всіх SHA-256 checks. Змінені або
    відсутні файли дають assets_incompatible до створення ML-моделі.
    """
    metadata = read_json(directory / "assets.json")
    for role, spec in MODEL_SPECS.items():
        item = metadata.get(role, {})
        if item.get("model") != spec["model"] or not item.get("files"):
            raise ValueError("assets_incompatible: model identity")
        for name, expected in item["files"].items():
            path = (directory / name).resolve()
            if not path.is_relative_to(directory.resolve()) or file_digest(path) != expected:
                raise ValueError("assets_incompatible: file hash")
    return metadata
