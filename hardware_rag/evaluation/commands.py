"""Командні операції eval/calibrate з явним provisional і повним gate."""

from ..artifacts import read_json
from ..config import ROOT
from ..ingestion.pipeline import current_dataset, load_dataset
from .dataset import lint, load_cases


def checked_cases(config, provisional: bool = False):
    """Читає frozen dataset/testset і блокує structural errors до API.

    Provisional послаблює тільки ручне approved, не IDs/proofs/coverage.
    Повертає envelope/cases/manifest/chunks для наступних стадій.
    """
    directory = current_dataset(config, ROOT)
    manifest, chunks = load_dataset(directory)
    envelope, cases = load_cases(config.path("testset"))
    problems = lint(envelope, cases, manifest, chunks, read_json(directory / "blocks.json"), require_review=not provisional)
    if problems:
        raise ValueError("testset_invalid:\n" + "\n".join(problems))
    return envelope, cases, manifest, chunks


def execute_eval(config, stage: str, provisional: bool = False, with_gate: bool = False) -> dict:
    """Виконує lint/retrieval/answers/full без автоматичного baseline update.

    --gate дозволено тільки для full і approved testset. Generator/judge
    використовують один Budget; retrieval/lint не потребують ключа API.
    Run artifacts пишуться навіть при провалі якісних порогів.
    """
    if with_gate and (provisional or stage != "full"):
        raise ValueError("gate потребує повного прогону approved-тестсету")
    envelope, cases, manifest, _ = checked_cases(config, provisional)
    if stage == "lint":
        return {"status": "testset_ok", "provisional": provisional, "count": len(cases)}
    from ..runtime import retrieval_runtime, approved_budget
    from ..generation.tokenization import LlmTokens
    from ..generation.client import LlmClient
    from .judge import Judge
    from .runner import run_retrieval, run_answers, save_run
    with retrieval_runtime(config, ROOT) as (_, _, retriever):
        retrieval = run_retrieval(retriever, cases) if stage in ("retrieval", "full") else None
        records, metrics, budget, judge = None, None, None, None
        if stage in ("answers", "full"):
            tokens = LlmTokens(config.path("assets"), config.tokenizer_encoding)
            budget = approved_budget(config)
            bot = LlmClient(config, tokens, budget)
            judge = Judge(LlmClient(config, tokens, budget, judge=True), ROOT)
            records, metrics = run_answers(retriever, cases, config.path("generator_prompt").read_text(encoding="utf-8"),
                                           bot, tokens, config, judge)
        calibration_path = config.path("runs") / "calibration.json"
        calibration_data = read_json(calibration_path) if calibration_path.exists() else None
        run = save_run(config, ROOT, manifest, envelope, records=records, retrieval=retrieval,
                       metrics=metrics, budget=budget, judge=judge, calibration_data=calibration_data)
        return {"run_id": run["run_id"], "metrics": run["metrics"], "gate_failures": run["gate_failures"],
                "provisional": run["provisional"], "cost_usd": run["cost_usd"],
                "exit_code": 1 if with_gate and run["gate_failures"] else 0}


def execute_calibration(config, run_id: str) -> dict:
    """Калібрує суддю за approved labels конкретного збереженого run.

    Відсутня ручна розмітка блокує API. Результат пишеться окремо,
    старий calibration.json не перезаписується автоматично.
    """
    from ..runtime import approved_budget
    from ..generation.tokenization import LlmTokens
    from ..generation.client import LlmClient
    from .judge import Judge
    from .calibrate import calibrate_run
    _, cases, manifest, chunks = checked_cases(config)
    run = read_json(config.path("runs") / run_id / "run.json")
    if run["dataset_id"] != manifest["dataset_id"]:
        raise ValueError("calibration: stale run dataset")
    tokens = LlmTokens(config.path("assets"), config.tokenizer_encoding)
    judge = Judge(LlmClient(config, tokens, approved_budget(config), judge=True), ROOT)
    return calibrate_run(run, cases, chunks, config.path("labels"), judge,
                         config.path("runs") / "calibration.json")
