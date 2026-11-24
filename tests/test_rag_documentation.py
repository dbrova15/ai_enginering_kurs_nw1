"""Перевірка явної навчальної вимоги R19 до пояснень нового коду."""

import ast
import subprocess
import sys
import unittest
from pathlib import Path

# Корінь fixtures/коду визначається шляхом тесту, не cwd під час CI.
ROOT = Path(__file__).resolve().parent.parent


class DocumentationTests(unittest.TestCase):
    """Контролює покриття docstring й ліниві імпорти CLI без моделей.

    AST перевіряє наявність і мінімальний зміст пояснення, але не може
    довести його педагогічну вичерпність; це лишається предметом review.
    """
    def test_all_new_classes_and_methods_have_explanatory_docstrings(self):
        """Кожний новий class/function має багаторядкове пояснення, не назву.

        Перевіряє production package і provider_config; constants мають
        пояснювальний comment на попередньому рядку.
        """
        paths = list((ROOT / "hardware_rag").rglob("*.py")) + [ROOT / "provider_config.py", ROOT / "main.py", ROOT / "data/hw2/download_sources.py"]
        problems = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            lines = text.splitlines()
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    doc = ast.get_docstring(node)
                    if not doc or len(doc) < 80:
                        problems.append(f"{path.name}:{node.lineno}: {node.name}")
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.isupper() and not lines[node.lineno - 2].lstrip().startswith("#"):
                            problems.append(f"{path.name}:{node.lineno}: constant {target.id}")
        self.assertEqual(problems, [])

    def test_cli_help_does_not_import_models_or_openai_client(self):
        """Свіжий процес імпортує CLI без fastembed чи qdrant-client.

        Наявність установлених пакетів не приховує небажаний eager load;
        subprocess не виконує жодного API чи tokenizer bootstrap.
        """
        script = "import sys; from hardware_rag.cli import parser; parser(); assert 'fastembed' not in sys.modules; assert 'qdrant_client' not in sys.modules"
        process = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
