"""Підготовка чистої копії main і виконання наявного quality gate."""

import json
import os
from decimal import Decimal
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
from types import SimpleNamespace

from ..artifacts import digest, read_json, write_json
from ..evaluation.judge import Judge
from ..eval_cases import HumanLabel
from .github import REPOSITORY, Run
from .ledger import Outcome, RUN_LIMIT

# Модель і промпт відповідають наявному прогону та калібруванню ДЗ2.
MODEL = "gpt-4o-mini"
# Чинний промпт baseline відповідає виміряній конфігурації.
GENERATOR_PROMPT = "prompts/rag/v1/system.txt"
# Індекс будується офлайн і має окремий час очікування.
INDEX_TIMEOUT = 20 * 60
# Платний процес має завершитися в межах очікування GitHub Actions.
EVAL_TIMEOUT = 30 * 60
# Обмеження для отримання коміту та локальної перевірки артефактів.
GIT_TIMEOUT = 120


def git_environment() -> dict:
    """Створює оточення Git без токенів і без локальних Git-налаштувань.

    Фіксований публічний HTTPS-репозиторій читається без credential helper.
    """
    return {
        "PATH": os.defpath, "LANG": "C.UTF-8", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
    }


def checkout_main(cache: Path, checkout: Path, run: Run) -> None:
    """Отримує main з GitHub і розпаковує лише коміт із перевіреної історії.

    Git-процеси не отримують ключів. Архів розгортається у порожню робочу
    копію з захистом від шляхів і посилань за межі каталогу.
    """
    env = git_environment()
    if not cache.exists():
        subprocess.run(["git", "init", "--bare", "--quiet", str(cache)], env=env, check=True, timeout=GIT_TIMEOUT)
    git = ["git", f"--git-dir={cache}"]
    subprocess.run(git + ["fetch", "--quiet", "--no-tags", f"https://github.com/{REPOSITORY}.git", "refs/heads/main"],
                   env=env, check=True, timeout=GIT_TIMEOUT)
    subprocess.run(git + ["merge-base", "--is-ancestor", run.sha, "FETCH_HEAD"],
                   env=env, check=True, timeout=GIT_TIMEOUT)
    subprocess.run(git + ["archive", "--format=tar", "-o", str(checkout.parent / "source.tar"), run.sha],
                             env=env, timeout=GIT_TIMEOUT, check=True)
    with tarfile.open(checkout.parent / "source.tar") as source:
        source.extractall(checkout, filter="data")
    if (checkout / ".env").exists() or (checkout / ".env").is_symlink():
        raise ValueError("CI checkout містить .env")


def verify_calibration(checkout: Path) -> None:
    """Звіряє калібрування з поточним суддею, розміткою і збереженим прогоном.

    Зміна цих артефактів має зупинити роботу до оплати. Докази й еталони
    не читаються звідси для побудови зовнішнього запиту.
    """
    evaluation = checkout / "evals/hw2"
    calibration = read_json(evaluation / "runs/calibration.json")
    labels = [HumanLabel.model_validate(label) for label in read_json(evaluation / "labels.json")["labels"]]
    current_judge = Judge(SimpleNamespace(model=MODEL), checkout)
    run_id = calibration["run_id"]
    if not isinstance(run_id, str) or re.fullmatch(r"[\w-]+", run_id) is None:
        raise ValueError("Некоректний ідентифікатор калібрувального прогону")
    original = read_json(evaluation / "runs" / run_id / "run.json")
    processed = checkout / "data/hw2/processed"
    dataset_id = read_json(processed / "current.json")["dataset_id"]
    if not isinstance(dataset_id, str) or re.fullmatch(r"[0-9a-f]{64}", dataset_id) is None:
        raise ValueError("Некоректний ідентифікатор корпусу")
    manifest = read_json(processed / dataset_id / "manifest.json")
    if (
        calibration["review_status"] != "approved"
        or not calibration["actual_models"]
        or len({label.case_id for label in labels if label.review_status == "approved"}) < 10
        or calibration["judge_identity"] != current_judge.identity
        or calibration["judge_identity"] != original["judge_identity"]
        or calibration["labels_sha256"] != digest([label.model_dump(mode="json") for label in labels])
        or original["testset_sha256"] != digest(read_json(evaluation / "testset.json"))
        or original["dataset_id"] != dataset_id
        or original["chunks_sha256"] != manifest["chunks_sha256"]
    ):
        raise ValueError("Калібрування застаріло або не підтверджено")


def prepare(checkout: Path, assets: Path, tariffs: dict) -> None:
    """Копіює локальні ваги, задає профіль і будує індекс без ключа OpenAI.

    Команда lint звіряє затверджені еталони, а index перевіряє хеші ваг.
    Тарифи беруться із затвердженого локального профілю.
    """
    verify_calibration(checkout)
    rag = checkout / ".rag"
    shutil.copytree(assets, rag / "models")
    profile = {key: tariffs[key] for key in (
        "input_usd_per_million", "output_usd_per_million", "pricing_date", "pricing_provider", "price_source",
    )}
    profile.update(paid_enabled=True, budget_usd=float(RUN_LIMIT), generator_prompt=GENERATOR_PROMPT)
    write_json(rag / "ci-paid.json", profile)
    invoke(checkout, ["eval", "--stage", "lint"], GIT_TIMEOUT).check_returncode()
    invoke(checkout, ["index"], INDEX_TIMEOUT).check_returncode()


def invoke(checkout: Path, args: list[str], timeout: int, key: str | None = None) -> subprocess.CompletedProcess:
    """Виконує штатний CLI з обмеженим оточенням і без передавання ключа аргументом.

    GitHub token та налаштування інших провайдерів залишаються за межами
    процесу. Результат захоплюється для локальної перевірки метрик і витрат.
    """
    env = {"PATH": os.defpath, "LANG": "C.UTF-8",
           "LLM_PROVIDER": "openai", "RAG_MODEL": MODEL, "RAG_JUDGE_MODEL": MODEL}
    if key is not None:
        env["OPENAI_API_KEY"] = key
    return subprocess.run(
        [sys.executable, "-B", "main.py", "rag", *args, "--config", ".rag/ci-paid.json"],
        cwd=checkout, env=env, capture_output=True, text=True, encoding="utf-8", timeout=timeout,
    )


def evaluate(checkout: Path, destination: Path, key: str) -> tuple[Outcome, Decimal | None]:
    """Запускає full gate, перевіряє завершений артефакт і зберігає його локально.

    Скасована команда або неповні дані лишають консервативний резерв.
    У GitHub публікується лише короткий результат, без сирих записів.
    """
    proc = invoke(checkout, ["eval", "--stage", "full", "--gate"], EVAL_TIMEOUT, key)
    if proc.returncode not in (0, 1):
        return Outcome("error", "RAG evaluation did not complete"), None
    result = json.loads(proc.stdout)
    run_id = result["run_id"]
    if re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{8}", run_id) is None or result["exit_code"] != proc.returncode:
        return Outcome("error", "Invalid evaluation output"), None
    artifacts = checkout / "evals/hw2/runs" / run_id
    saved = read_json(artifacts / "run.json")
    if saved["cost_usd"] != result["cost_usd"] or saved["gate_failures"] != result["gate_failures"]:
        return Outcome("error", "Evaluation artifact mismatch"), None
    shutil.copytree(artifacts, destination)
    accounted = Decimal(saved["cost_usd"])
    if not accounted.is_finite() or not 0 <= accounted <= RUN_LIMIT:
        return Outcome("error", "RAG usage exceeded the approved budget"), None
    cost = None if saved["usage_unknown_calls"] else accounted
    if proc.returncode == 0 and not result["provisional"] and not result["gate_failures"]:
        return Outcome("success", "RAG retrieval and answer thresholds passed"), cost
    return Outcome("failure", "One or more RAG quality thresholds failed"), cost
