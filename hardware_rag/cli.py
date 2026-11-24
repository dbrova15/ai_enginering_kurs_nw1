"""Лінивий CLI ДЗ2: argparse і маршрутизація, без ML-роботи при --help."""

import argparse
import json
import re
from pathlib import Path
from .config import ROOT, load_config
from .artifacts import within


def parser() -> argparse.ArgumentParser:
    """Описує команди ДЗ2 без імпорту ONNX, Qdrant або API-клієнта.

    --config можна передати до або після назви команди; --provisional
    не сумісний із фінальним --gate. Шляхи дозволено лише у workspace.
    """
    result = argparse.ArgumentParser(description="HardwareResearch: RAG на власних даних")
    result.add_argument("--config", type=Path)
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("prepare-models", "inventory", "ingest", "compare-chunking", "index", "ask", "eval", "calibrate", "report"):
        command = commands.add_parser(name)
        command.add_argument("--config", type=Path, default=argparse.SUPPRESS)
        if name == "prepare-models":
            command.add_argument("--download", action="store_true")
        if name in ("inventory", "compare-chunking", "report"):
            command.add_argument("--output", type=Path)
        if name == "ask":
            command.add_argument("--question", required=True)
            command.add_argument("--language", choices=("uk", "en", "ru"))
            command.add_argument("--format", choices=("html", "pdf"))
        if name == "eval":
            command.add_argument("--stage", choices=("lint", "retrieval", "answers", "full"), default="full")
            command.add_argument("--provisional", action="store_true")
            command.add_argument("--gate", action="store_true")
        if name in ("calibrate", "report"):
            command.add_argument("--run-id", required=True)
    return result


def dispatch(args, config):
    """Викликає один відповідальний модуль і повертає його JSON-результат.

    Не додає приховані download/index/API дії. Кожна команда має явні
    prerequisites; непідготовлений corpus чи бюджет відхиляються.
    """
    from . import commands
    if args.command == "prepare-models":
        return commands.prepare(config, args.download)
    if args.command == "inventory":
        from .ingestion.inventory import inventory
        return inventory(ROOT, within(ROOT, str(args.output)) if args.output else None)
    if args.command == "ingest":
        return commands.ingest(config)
    if args.command == "compare-chunking":
        return commands.compare_chunking(config, within(ROOT, str(args.output or "evals/hw2/chunking-comparison.json")))
    if args.command == "index":
        return commands.index(config)
    if args.command == "ask":
        return commands.ask(config, args.question, args.language, args.format)
    if args.command == "eval":
        from .evaluation.commands import execute_eval
        return execute_eval(config, args.stage, args.provisional, args.gate)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.run_id):
        raise ValueError("Некоректний run-id")
    if args.command == "calibrate":
        from .evaluation.commands import execute_calibration
        return execute_calibration(config, args.run_id)
    from .evaluation.reporting import write_report
    path = within(ROOT, str(args.output or "evals/hw2/REPORT.md"))
    write_report(path, config.path("runs") / args.run_id / "run.json")
    return {"report": str(path)}


def main(argv: list[str] | None = None) -> int:
    """Запускає CLI й повертає 0/1/2 для success/gate failure/runtime error.

    Технічна невдача не маскується як not_found. Статичні schema/config
    повідомлення безпечні для журналу; provider error bodies очищає adapter.
    """
    args = parser().parse_args(argv)
    try:
        config_path = within(ROOT, str(args.config)) if args.config else None
        data = dispatch(args, load_config(config_path))
        if "answer" in data:
            print(data["answer"])
            print("Журнал:", data["record"])
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
        return data.get("exit_code", 0)
    except Exception as error:
        # Native ONNX/NumPy errors теж є incomplete. Сирі сторонні bodies
        # не друкуються; власні validation/path повідомлення лишаються корисними.
        message = str(error) if isinstance(error, (ValueError, OSError, KeyError)) else type(error).__name__
        print(f"RAG incomplete/error: {message}")
        return 2
