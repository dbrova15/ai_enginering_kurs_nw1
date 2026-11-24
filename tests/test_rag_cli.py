"""Контракт CLI для технічних збоїв без справжніх models/API або секретів."""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from hardware_rag.cli import main


class CliFailureTests(unittest.TestCase):
    """Перевіряє incomplete exit code та безпечне повідомлення користувачеві.

    Native model failure не повинен виглядати як якісна відмова not_found
    або друкувати довільний exception body стороннього runtime.
    """
    def test_native_failure_is_incomplete_without_raw_body(self):
        """Імітує runtime allocation failure без завантаження великих ваг.

        Контрольована помилка проходить саме через main/dispatch boundary:
        перевіряються exit 2, видимий тип і відсутність небезпечного body.
        """
        output = io.StringIO()
        with patch("hardware_rag.cli.dispatch", side_effect=RuntimeError("private-provider-body")), redirect_stdout(output):
            code = main(["index"])
        self.assertEqual(code, 2)
        self.assertIn("RuntimeError", output.getvalue())
        self.assertNotIn("private-provider-body", output.getvalue())
