"""Офлайн-перевірки меж довіри, витрат і повторних запусків CI."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import httpx

from hardware_rag.ci.github import GitHub, REPOSITORY, Run
from hardware_rag.ci.ledger import Ledger, Outcome
from hardware_rag.ci.runner import process_run


class BudgetLedgerTests(unittest.TestCase):
    """Перевіряє, що перервані і паралельні запуски не перевитрачають бюджет."""

    def test_reservations_are_atomic_and_restart_preserves_spend(self):
        """Паралельні заявки отримують лише десять резервів і не дублюються."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "budget.sqlite"
            ledger = Ledger(path)
            with ThreadPoolExecutor(max_workers=8) as pool:
                allowed = list(pool.map(lambda ident: ledger.reserve(ident, "2026-11"), range(20)))
            self.assertEqual(sum(allowed), 10)
            reopened = Ledger(path)
            reopened.recover()
            self.assertFalse(reopened.reserve(20, "2026-11"))
            self.assertTrue(reopened.reserve(21, "2026-12"))
            self.assertFalse(reopened.reserve(21, "2027-01"))
            self.assertEqual(reopened.outcome(allowed.index(True)).state, "error")

    def test_measured_cost_releases_reserve_but_unknown_cost_does_not(self):
        """Відомий usage уточнює облік, а завершений запуск не оплачується вдруге."""
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "budget.sqlite")
            for ident in range(10):
                self.assertTrue(ledger.reserve(ident, "2026-11"))
            ledger.finish(0, Outcome("failure", "Quality threshold failed"), None)
            self.assertFalse(ledger.reserve(10, "2026-11"))
            ledger.finish(1, Outcome("success", "Passed"), Decimal("0.02636085"))
            self.assertFalse(ledger.reserve(11, "2026-11"))
            ledger.finish(2, Outcome("success", "Passed"), Decimal("0.02636085"))
            self.assertTrue(ledger.reserve(12, "2026-11"))
            self.assertEqual(ledger.outcome(1), Outcome("success", "Passed"))


class RunAdmissionTests(unittest.TestCase):
    """Перевіряє точний push та статус, створений GitHub Actions."""

    def setUp(self):
        """Створює приклад активної події з двома однаковими репозиторіями."""
        self.payload = {
            "id": 169, "event": "push", "status": "in_progress", "head_branch": "main",
            "head_sha": "a" * 40, "repository": {"full_name": REPOSITORY},
            "head_repository": {"full_name": REPOSITORY},
        }
        self.run_record = Run(169, "a" * 40)

    def test_rejects_pull_requests_forks_inactive_events_and_bad_shas(self):
        """Перевірка відсіює чужу гілку, репозиторій, подію та некоректний SHA."""
        self.assertEqual(Run.from_payload(self.payload), self.run_record)
        for change in (
            {"event": "pull_request"}, {"head_branch": "feature"}, {"status": "completed"},
            {"head_repository": {"full_name": "fork/project"}}, {"head_sha": "--help"},
            {"repository": {"full_name": "other/project"}}, {"id": True},
        ):
            with self.subTest(change=change):
                self.assertIsNone(Run.from_payload({**self.payload, **change}))

    def test_requires_pending_marker_from_github_actions_for_exact_run(self):
        """Маркер від іншого автора, іншого запуску або завершений статус відхиляється."""
        github = GitHub("test")
        github.client.close()
        marker = {"context": self.run_record.context, "state": "pending",
                  "target_url": self.run_record.url, "creator": {"login": "github-actions[bot]"}}

        def respond(request):
            """Надає локальну відповідь API активного запуску або його commit status."""
            data = self.payload if "/actions/runs/" in request.url.path else [marker]
            return httpx.Response(200, json=data)

        with httpx.Client(base_url=f"https://api.github.com/repos/{REPOSITORY}/",
                          transport=httpx.MockTransport(respond)) as client:
            github.client = client
            self.assertTrue(github.ready(self.run_record))
            marker["creator"] = {"login": "another-user"}
            self.assertFalse(github.ready(self.run_record))
            marker["creator"] = {"login": "github-actions[bot]"}
            marker["state"] = "success"
            self.assertFalse(github.ready(self.run_record))

    def test_retrying_publication_does_not_repeat_evaluation(self):
        """Результат фіксується до GitHub-запиту, а втрата відповіді не повторює оплату."""
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            ledger = Ledger(state / "budget.sqlite")
            github = Mock()
            github.ready.return_value = True
            github.publish.side_effect = [httpx.ConnectError("test"), None]
            with patch("hardware_rag.ci.runner.checkout_main"), patch("hardware_rag.ci.runner.prepare"), \
                 patch("hardware_rag.ci.runner.evaluate", return_value=(Outcome("success", "Passed"), Decimal("0.02"))) as call:
                with self.assertRaises(httpx.ConnectError):
                    process_run(self.run_record, github, ledger, state, state, {}, "test")
                process_run(self.run_record, github, ledger, state, state, {}, "test")
            self.assertEqual(call.call_count, 1)
            self.assertEqual(github.publish.call_count, 2)
