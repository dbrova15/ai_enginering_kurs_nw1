"""Локальні транзакції резерву, обліку і дедуплікації платних запусків."""

from contextlib import closing
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
import sqlite3

# Цілі мікродолари унеможливлюють округлення резерву вниз.
RUN_LIMIT = Decimal("0.10")
# Узгоджене співвідношення долара та цілої одиниці журналу.
MICRO_USD = 1_000_000
# Резерв на один запуск дорівнює повному ліміту CLI.
RUN_RESERVE = int(RUN_LIMIT * MICRO_USD)
# Один долар на місяць за часом UTC.
MONTH_LIMIT = MICRO_USD


@dataclass(frozen=True)
class Outcome:
    """Кінцевий статус GitHub і коротка причина без контексту або секретів.

    Такий запис можна повторно публікувати, не виконуючи оцінювання ще раз.
    """

    state: str
    description: str


class Ledger:
    """Зберігає бюджет та результати навіть після перезапуску локального runner.

    Транзакція SQLite захищає від одночасного резервування одного залишку.
    """

    def __init__(self, path: Path):
        """Створює журнал у приватному каталозі, якщо його ще немає.

        Ідентифікатор запуску є ключем дедуплікації незалежно від місяця.
        """
        self.path = path
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id INTEGER PRIMARY KEY, month TEXT NOT NULL, amount INTEGER NOT NULL,
                    state TEXT NOT NULL, description TEXT NOT NULL
                )
            """)

    def recover(self) -> None:
        """Позначає перервані запуски помилкою, зберігаючи весь резерв.

        Викликається після отримання блокування процесу, коли відомо, що
        попередній runner уже не змінює журнал.
        """
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                "UPDATE runs SET state = 'error', description = 'Local runner interrupted' WHERE state = 'running'"
            )

    def outcome(self, run_id: int) -> Outcome | None:
        """Дає вже готовий результат або None для ще незавершеного запуску.

        Завершений запис можна перепублікувати без повторного платного виклику.
        """
        with closing(sqlite3.connect(self.path)) as connection:
            row = connection.execute(
                "SELECT state, description FROM runs WHERE run_id = ? AND state <> 'running'", (run_id,)
            ).fetchone()
        return Outcome(*row) if row is not None else None

    def reserve(self, run_id: int, month: str) -> bool:
        """Резервує $0,10 тоді, коли запуск новий і місячний ліміт дозволяє.

        BEGIN IMMEDIATE робить перевірку суми і запис неподільними. Якщо
        місячного залишку замало, лишає кінцеву помилку без API-виклику.
        """
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT 1 FROM runs WHERE run_id = ?", (run_id,)).fetchone():
                return False
            spent = connection.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM runs WHERE month = ?", (month,)
            ).fetchone()[0]
            allowed = spent + RUN_RESERVE <= MONTH_LIMIT
            record = ("running", "", RUN_RESERVE) if allowed else ("error", "Monthly budget exhausted", 0)
            state, description, amount = record
            connection.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?)", (run_id, month, amount, state, description))
            return allowed

    def finish(self, run_id: int, outcome: Outcome, cost: Decimal | None) -> None:
        """Фіксує результат і уточнює резерв, якщо вартість підтверджено.

        Вартості поза погодженим діапазоном і невідомий usage залишають
        повний резерв. Округлення до мікродолара відбувається вгору.
        """
        amount = RUN_RESERVE
        if cost is not None and cost.is_finite() and 0 <= cost <= RUN_LIMIT:
            amount = int((cost * MICRO_USD).to_integral_value(rounding=ROUND_CEILING))
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                "UPDATE runs SET state = ?, description = ?, amount = ? WHERE run_id = ? AND state = 'running'",
                (outcome.state, outcome.description, amount, run_id),
            )
