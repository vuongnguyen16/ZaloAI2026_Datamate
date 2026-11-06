"""Submission-only last resort. No business tables, answers or old checkpoints."""

import json
import sqlite3
import uuid
from contextlib import closing
from pathlib import Path

from datamate.json_routing import project_id
from datamate.prediction_store import publish, publish_chunks, safe_path
from datamate.runtime_paths import (
    OutputBusyError,
    disjoint,
    ignored_output_entries,
    is_link,
    output_layout,
    publication_lock,
)
from datamate.scoring import parse_object, validate_entry

MAX_ROUTING_LINE = 1024 * 1024


def _line(value):
    return (
        json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _submission_line(record):
    raw = _line(record)
    validate_entry(parse_object(raw))
    return raw


def _admit(input_dir, output):
    source = Path(input_dir).resolve(strict=True)
    output = safe_path(output)
    if not disjoint(source, output):
        raise ValueError("failsafe output must be disjoint from input")
    output_layout(output)
    return source, output


def run_failsafe(input_dir, output, primary_error):
    _, output = _admit(input_dir, output)
    with publication_lock(output):
        return _run_failsafe(input_dir, output, primary_error)


def _run_failsafe(input_dir, output, primary_error):
    source, output = _admit(input_dir, output)
    ignored_entries = ignored_output_entries(output)
    final = safe_path(output / "submission.jsonl")
    if final.exists():
        raise FileExistsError("existing submission preserved")
    questions = source / "questions.jsonl"
    if is_link(questions) or not questions.is_file():
        raise ValueError("failsafe requires a regular questions file")
    # The resolved /data ancestor and read-only hardlinks are permitted here.
    # State is new per attempt and never reads an identity-mismatched checkpoint.
    scratch = safe_path(output / "logs" / f"failsafe-{uuid.uuid4().hex}")
    scratch.mkdir(parents=True, exist_ok=False)
    count = errors = routing_limits = 0
    with closing(sqlite3.connect(scratch / "ids.sqlite")) as database:
        database.execute("PRAGMA cache_size=-2048")
        database.execute("PRAGMA temp_store=FILE")
        database.execute("CREATE TABLE ids(qid TEXT PRIMARY KEY) WITHOUT ROWID")
        with questions.open("rb") as handle:
            index = 0
            while line := handle.readline(MAX_ROUTING_LINE + 1):
                index += 1
                if len(line) > MAX_ROUTING_LINE:
                    while line and not line.endswith(b"\n"):
                        line = handle.readline(MAX_ROUTING_LINE + 1)
                    routing_limits += 1
                    continue
                try:
                    line = line.removeprefix(b"\xef\xbb\xbf") if index == 1 else line
                    # Check syntax and ID only; never decode arbitrary value fields.
                    qid = project_id(line)
                    qid.encode("utf-8")
                    database.execute("INSERT OR IGNORE INTO ids VALUES (?)", (qid,))
                except (ValueError, UnicodeError, ArithmeticError, RecursionError):
                    errors += 1
                if index % 1000 == 0:
                    database.commit()
        database.commit()
        count = database.execute("SELECT count(*) FROM ids").fetchone()[0]

        def rows():
            for (qid,) in database.execute("SELECT qid FROM ids ORDER BY qid"):
                yield {"id": qid, "type": "abstain", "reason": "runtime_fallback"}

        publication = publish_chunks(
            final, (_submission_line(r) for r in rows()), allow_exclusive_fallback=True
        )
        logs = safe_path(output / "logs" / f"submission-{publication['sha256']}")
        logs.mkdir(parents=True, exist_ok=True)
        for index, record in enumerate(rows()):
            event = {
                "question_id": record["id"],
                "stage": "failsafe",
                "status": "abstain",
                "answer": record,
                "reason": "runtime_fallback",
                "primary_error": primary_error,
                "duration_seconds": 0,
                "timing_available": False,
                "evidence": "Submission fallback: IDs routed from questions only; no gold/business/checkpoint read.",
            }
            publish(
                logs / f"{index:06d}.json",
                _line(event),
                allow_exclusive_fallback=True,
            )
    outcome = {
        "valid": count > 0 and routing_limits == 0,
        "mode": "failsafe_all_abstain",
        "question_ids": count,
        "malformed_lines": errors,
        "routing_limit_lines": routing_limits,
        "coverage_complete": routing_limits == 0,
        "primary_error": primary_error,
        "publication": publication,
        "gold_content_read": False,
        "ignored_output_entries": ignored_entries,
    }
    publish(
        scratch / "diagnostics.json",
        _line(outcome),
        allow_exclusive_fallback=True,
    )
    return outcome


def submission_predict(input_dir, output, *, config_path=None, started=None):
    try:
        _, output = _admit(input_dir, output)
        with publication_lock(output):
            return _submission_predict_locked(
                input_dir, output, config_path=config_path, started=started
            )
    except OutputBusyError:
        return {"valid": False, "mode": "output_busy", "gold_content_read": False}
    except Exception as exc:
        return {
            "valid": False,
            "mode": "output_refused",
            "error": type(exc).__name__,
            "gold_content_read": False,
        }


def _submission_predict_locked(input_dir, output, *, config_path=None, started=None):
    try:
        import yaml

        from datamate.prediction import run_predict

        config = None
        if config_path is not None:
            config = yaml.safe_load(Path(config_path).read_text("utf-8"))
            if not isinstance(config, dict):
                raise ValueError("prediction config must be a mapping")
        return run_predict(
            input_dir, output, config, started=started, allow_exclusive_fallback=True
        )
    except Exception as primary:
        try:
            return run_failsafe(input_dir, output, type(primary).__name__)
        except Exception as fallback:
            return {
                "valid": False,
                "mode": "failsafe_failed",
                "primary_error": type(primary).__name__,
                "fallback_error": type(fallback).__name__,
                "gold_content_read": False,
            }
