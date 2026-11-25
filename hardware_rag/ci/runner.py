"""Локальна служба CI спостерігає за погодженим workflow і виконує його оцінку."""

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
from pathlib import Path
import tempfile
import time

from dotenv import dotenv_values
import httpx

from ..artifacts import read_json
from ..config import ROOT
from ..generation.budget import Budget
from .execution import checkout_main, evaluate, prepare
from .github import GitHub, Run
from .ledger import Ledger, Outcome, RUN_LIMIT

# Інтервал між опитуваннями GitHub.
POLL_SECONDS = 30


def process_run(run: Run, github: GitHub, ledger: Ledger, state: Path,
                assets: Path, tariffs: dict, key: str) -> None:
    """Готує конкретний SHA, резервує бюджет і виконує оцінювання максимум один раз.

    Пропускає запуски без запиту GitHub. Записує фінальний результат до
    публікації, щоб повтор публікації не повторював виклики OpenAI.
    """
    if not github.ready(run):
        return
    previous = ledger.outcome(run.id)
    if previous:
        github.publish(run, previous.state, previous.description)
        return
    with tempfile.TemporaryDirectory(dir=state, prefix="checkout-") as scratch:
        checkout = Path(scratch) / "source"
        checkout.mkdir()
        try:
            checkout_main(state / "source.git", checkout, run)
            prepare(checkout, assets, tariffs)
        except Exception as error:
            print(f"Запуск {run.id}, підготовка: {type(error).__name__}", flush=True)
            github.publish(run, "error", "Local checkout, assets or calibration are invalid")
            return
        if not github.ready(run):
            return
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        if not ledger.reserve(run.id, month):
            rejected = ledger.outcome(run.id)
            if rejected:
                github.publish(run, rejected.state, rejected.description)
            return
        try:
            outcome, cost = evaluate(checkout, state / "results" / str(run.id), key)
        except Exception as error:
            print(f"Запуск {run.id}, оцінювання: {type(error).__name__}", flush=True)
            outcome, cost = Outcome("error", "RAG evaluation interrupted or invalid"), None
        ledger.finish(run.id, outcome, cost)
        github.publish(run, outcome.state, outcome.description)
        print(f"Запуск {run.id}: {outcome.state}", flush=True)


def poll(github: GitHub, ledger: Ledger, state: Path, assets: Path, tariffs: dict, key: str, once: bool) -> None:
    """Послідовно обслуговує активні запити, даючи повторити мережевий збій GitHub.

    Після помилки API статусів цикл перечитує події. Бюджет і завершені
    результати беруться з SQLite, тому вже оцінений запуск не оплачується знову.
    """
    while True:
        try:
            for run in github.active():
                process_run(run, github, ledger, state, assets, tariffs, key)
        except httpx.HTTPError as error:
            status = error.response.status_code if isinstance(error, httpx.HTTPStatusError) else "мережа"
            print(f"GitHub API недоступний ({status})", flush=True)
            if once:
                raise SystemExit(2) from None
        if once:
            return
        time.sleep(POLL_SECONDS)


def main() -> None:
    """Перевіряє локальні облікові дані і запускає єдиний екземпляр служби.

    .env читається тільки на цій машині. Каталог стану має бути приватним.
    Без ключів, моделей або затвердженого тарифу мережевий цикл не стартує.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--state", type=Path, default=Path.home() / ".local/state/hardware-rag-ci")
    parser.add_argument("--assets", type=Path, default=ROOT / ".rag/models")
    parser.add_argument("--tariffs", type=Path, default=ROOT / ".rag/paid-run.json")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    credentials = dotenv_values(args.env_file, interpolate=False)
    token = (credentials.get("HW2_CI_GITHUB_TOKEN") or "").strip()
    key = (credentials.get("OPENAI_API_KEY") or "").strip()
    if not token or not key:
        parser.error("Локальний .env має містити HW2_CI_GITHUB_TOKEN і OPENAI_API_KEY")
    assets = args.assets.resolve()
    if not (assets / "assets.json").is_file():
        parser.error("Потрібні підготовлені локальні моделі з assets.json")
    tariffs = read_json(args.tariffs)
    if tariffs.get("pricing_provider") != "openai" or not tariffs.get("pricing_date") or not tariffs.get("price_source"):
        parser.error("Потрібен погоджений локальний тариф OpenAI")
    for field in ("input_usd_per_million", "output_usd_per_million"):
        if Decimal(str(tariffs[field])) <= 0:
            parser.error("Тариф має бути додатним")
    Budget(float(RUN_LIMIT), tariffs["input_usd_per_million"], tariffs["output_usd_per_million"])
    state = args.state.resolve()
    if state.is_relative_to(ROOT):
        parser.error("Каталог стану має бути поза репозиторієм")
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    if state.stat().st_mode & 0o077:
        parser.error("Каталог стану має бути приватним")
    with (state / "runner.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error("Цей локальний runner уже працює")
        ledger = Ledger(state / "budget.sqlite")
        ledger.recover()
        github = GitHub(token)
        try:
            poll(github, ledger, state, assets, tariffs, key, args.once)
        finally:
            github.client.close()


if __name__ == "__main__":
    main()
