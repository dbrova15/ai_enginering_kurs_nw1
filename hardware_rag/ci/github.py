"""Читання довірених запусків і публікація стисненого статусу в GitHub."""

from dataclasses import dataclass
import re

import httpx

# Прив'язка до конкретного репозиторію обмежує роботу токена і runner.
REPOSITORY = "dbrova15/ai_enginering_kurs_nw1"
# Тільки цей workflow створює заявку на платне оцінювання.
WORKFLOW = "hw2-answer-gate.yml"
# Контекст прив'язаний до запуску, навіть коли GitHub повторно використовує SHA.
STATUS_PREFIX = "hw2/answer-gate/"


@dataclass(frozen=True)
class Run:
    """Зберігає перевірені ідентифікатори запуску для статусу і журналу.

    Обидва значення потрібні, бо кілька запусків можуть мати той самий SHA.
    """

    id: int
    sha: str

    @classmethod
    def from_payload(cls, payload: dict) -> "Run | None":
        """Приймає лише активний push у main заданого репозиторію.

        Перевірка форми SHA потрібна перед використанням як Git-аргументу.
        Інші події й репозиторії відсіюються до резервування бюджету.
        """
        sha = payload.get("head_sha")
        ident = payload.get("id")
        if (
            payload.get("event") != "push"
            or payload.get("status") != "in_progress"
            or payload.get("head_branch") != "main"
            or (payload.get("repository") or {}).get("full_name") != REPOSITORY
            or (payload.get("head_repository") or {}).get("full_name") != REPOSITORY
            or type(ident) is not int
            or ident <= 0
            or not isinstance(sha, str)
            or re.fullmatch(r"[0-9a-f]{40}", sha) is None
        ):
            return None
        return cls(ident, sha)

    @property
    def url(self) -> str:
        """Повертає власну сторінку запуску на фіксованому домені GitHub.

        Адреса використовується для прив'язки статусу до точного запуску.
        """

        return f"https://github.com/{REPOSITORY}/actions/runs/{self.id}"

    @property
    def context(self) -> str:
        """Формує контекст статусу з run ID, щоб розрізняти запуски одного SHA.

        Префікс однаковий для локального runner та GitHub workflow.
        """

        return f"{STATUS_PREFIX}{self.id}"


class GitHub:
    """Ізолює GitHub REST API та залишає облікові дані в локальному процесі.

    Приймає запуски з дозволеного репозиторію та повертає лише статус оцінки.
    """

    def __init__(self, token: str):
        """Встановлює фіксоване джерело REST і забороняє автоматичні перенаправлення.

        Token передається заголовком, тому його не видно в аргументах процесу.
        """
        self.client = httpx.Client(
            base_url=f"https://api.github.com/repos/{REPOSITORY}/",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=20,
            follow_redirects=False,
            trust_env=False,
        )

    def active(self) -> list[Run]:
        """Повертає активні дозволені запуски, починаючи з найстарішого.

        Вузький фільтр API доповнює локальну перевірку кожної події.
        """
        response = self.client.get(f"actions/workflows/{WORKFLOW}/runs", params={
            "branch": "main", "event": "push", "status": "in_progress", "per_page": 100,
        })
        response.raise_for_status()
        runs = (Run.from_payload(item) for item in response.json()["workflow_runs"])
        return sorted((run for run in runs if run is not None), key=lambda run: run.id)

    def ready(self, run: Run) -> bool:
        """Перевіряє, що запуск досі активний і workflow залишив запит pending.

        Перевірка після побудови індексу відсіює скасовані або прострочені запуски.
        """
        response = self.client.get(f"actions/runs/{run.id}")
        response.raise_for_status()
        if Run.from_payload(response.json()) != run:
            return False
        response = self.client.get(f"commits/{run.sha}/statuses", params={"per_page": 100})
        response.raise_for_status()
        marker = next((item for item in response.json() if item["context"] == run.context), None)
        return (
            marker is not None and marker["state"] == "pending" and marker["target_url"] == run.url
            and marker["creator"]["login"] == "github-actions[bot]"
        )

    def publish(self, run: Run, state: str, description: str) -> None:
        """Публікує лише короткий результат для конкретних SHA та run ID.

        Готовий результат зберігається в SQLite до цього запиту. Повторний
        виклик після втрати мережі не запускає OpenAI знову.
        """
        response = self.client.post(f"statuses/{run.sha}", json={
            "state": state, "description": description, "context": run.context, "target_url": run.url,
        })
        response.raise_for_status()
