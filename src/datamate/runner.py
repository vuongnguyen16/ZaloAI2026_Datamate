"""CPU wiring smoke, deliberately limited to a tiny, trusted synthetic fixture.

The DuckDB connection here is not the untrusted SQL worker needed by group D.
"""

import csv
import json
import time
from decimal import Decimal
from pathlib import Path

import duckdb

from datamate.artifacts import manifest, new_run, write_json
from datamate.config import load_config
from datamate.contracts import FakeResponse, Question, Submission, json_object


def read_questions(path: Path, limit: int | None = None) -> list[Question]:
    questions = []
    seen = set()
    with path.open(encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                raise ValueError(f"blank question line {line_number}")
            try:
                question = Question.model_validate(json_object(line))
            except ValueError as exc:
                raise ValueError(
                    f"invalid question at line {line_number}: {exc}"
                ) from exc
            if question.id in seen:
                raise ValueError(
                    f"duplicate question id at line {line_number}: {question.id}"
                )
            seen.add(question.id)
            questions.append(question)
            if limit is not None and len(questions) > limit:
                raise ValueError("question count exceeds local budget")
    if not questions:
        raise ValueError("questions file is empty")
    return questions


class FakeModelAdapter:
    """Return fixture responses in order. No model imports, weights or network."""

    def __init__(self, responses: list):
        self.responses = iter(responses)

    def generate(self, question: Question) -> FakeResponse:
        # A real group D adapter will consume question/context. This checks wiring only.
        return FakeResponse.model_validate(next(self.responses))


def write_results(
    run_dir: Path, predictions: list[Submission], events: list[dict]
) -> None:
    lines = "".join(
        json.dumps(p.output(), ensure_ascii=False, allow_nan=False) + "\n"
        for p in predictions
    )
    (run_dir / "submission.jsonl").write_text(lines, encoding="utf-8")
    (run_dir / "predictions.jsonl").write_text(lines, encoding="utf-8")
    (run_dir / "events.jsonl").write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events),
        encoding="utf-8",
    )
    # Indexed filenames avoid treating untrusted IDs as filesystem paths.
    for index, event in enumerate(events):
        write_json(run_dir / "logs" / f"{index:06d}.json", event)


def run_smoke(config_path: Path) -> Path:
    config, input_dir, output_root = load_config(config_path)
    questions = read_questions(input_dir / "questions.jsonl", config.max_questions)
    responses = json.loads((input_dir / "responses.json").read_text("utf-8"))
    if not isinstance(responses, list) or len(responses) != len(questions):
        raise ValueError("fake response count must match question count")
    adapter = FakeModelAdapter(responses)
    # Only this synthetic schema is supported. General ingestion belongs to group A.
    with (input_dir / "sales.csv").open(encoding="utf-8", newline="") as handle:
        rows = [(row["code"], Decimal(row["amount"])) for row in csv.DictReader(handle)]
    run_dir = new_run(output_root, "smoke")
    root = Path(__file__).resolve().parents[2]
    inputs = [
        config_path.resolve(),
        *sorted(p for p in input_dir.iterdir() if p.is_file()),
    ]
    record = manifest(root, inputs, "smoke", run_dir.name)
    record["seed"] = config.seed
    write_json(run_dir / "manifest.json", record)
    write_json(
        run_dir / "config.resolved.json",
        {
            **config.model_dump(),
            "input_dir": str(input_dir),
            "output_root": str(output_root),
        },
    )
    predictions, events = [], []
    with duckdb.connect(
        config={
            "threads": config.local_cpu_threads,
            "memory_limit": f"{config.memory_limit_mb}MB",
            "enable_external_access": False,
        }
    ) as connection:
        connection.execute("CREATE TABLE sales(code VARCHAR, amount DECIMAL(18,2))")
        connection.executemany("INSERT INTO sales VALUES (?, ?)", rows)
        for question in questions:
            started = time.perf_counter()
            event = {
                "run_id": run_dir.name,
                "question_id": question.id,
                "stage": "smoke",
            }
            try:
                response = adapter.generate(question)
                event["sql"] = response.sql
                result = connection.execute(response.sql).fetchall()
                if len(result) != 1 or len(result[0]) != 1 or result[0][0] is None:
                    raise ValueError(
                        "synthetic scalar response must be exactly one non-null cell"
                    )
                value = result[0][0]
                if isinstance(value, Decimal):
                    value = (
                        int(value)
                        if value == value.to_integral_value()
                        else float(value)
                    )
                prediction = Submission(
                    id=question.id, type=response.answer_type, answer=value
                )
                event.update(status="ok", rows=[[value]], truncated=False)
            except (ValueError, StopIteration, duckdb.Error) as exc:
                prediction = Submission(id=question.id, type="abstain")
                event.update(
                    status="error", error_type=type(exc).__name__, error=str(exc)
                )
            event.update(
                answer=prediction.output(),
                duration_seconds=time.perf_counter() - started,
            )
            predictions.append(prediction)
            events.append(event)
    write_results(run_dir, predictions, events)
    write_json(
        run_dir / "summary.json",
        {
            "mode": "synthetic_fake_smoke",
            "questions": len(questions),
            "errors": sum(e["status"] == "error" for e in events),
            "gpu": "not_tested",
            "pa": "not_evaluated",
        },
    )
    return run_dir


def run_stub(input_dir: Path, output_dir: Path) -> Path:
    """Format-only stub: never reads answers, business files or rule semantics."""
    input_dir = input_dir.resolve(strict=True)
    output_dir = output_dir.resolve()
    if output_dir == input_dir or input_dir in output_dir.parents:
        raise ValueError("output must be outside input directory")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("stub output directory must be new or empty")
    questions = read_questions(input_dir / "questions.jsonl", limit=10000)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "logs").mkdir(exist_ok=True)
    predictions, events = [], []
    for question in questions:
        started = time.perf_counter()
        prediction = Submission(id=question.id, type="abstain")
        predictions.append(prediction)
        events.append(
            {
                "question_id": question.id,
                "stage": "format_stub",
                "status": "abstain",
                "answer": prediction.output(),
                "duration_seconds": time.perf_counter() - started,
                "evidence": "Format-only stub; no model or business query executed.",
            }
        )
    write_results(output_dir, predictions, events)
    root = Path(__file__).resolve().parents[2]
    write_json(
        output_dir / "manifest.json",
        manifest(
            root,
            [
                input_dir / name
                for name in ("questions.jsonl", "rulebook.md", "calendar.csv")
                if (input_dir / name).is_file()
            ],
            "format_stub",
            output_dir.name,
        ),
    )
    write_json(
        output_dir / "summary.json",
        {
            "mode": "format_stub",
            "questions": len(questions),
            "abstain": len(questions),
            "gpu": "not_tested",
            "pa": "not_evaluated",
        },
    )
    return output_dir
