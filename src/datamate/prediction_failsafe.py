"""Submission-only last resort. No business tables, answers or old checkpoints."""

import sqlite3
import uuid
from contextlib import closing
from pathlib import Path

from datamate.ingest.loader import disjoint, is_link
from datamate.prediction_store import publish, publish_chunks, safe_path
from datamate.scoped_data import project_id
from datamate.serialization import exact_json, submission_bytes

MAX_ROUTING_LINE = 1024 * 1024


def run_failsafe(input_dir, output, primary_error):
    source = Path(input_dir).resolve(strict=True)
    output = safe_path(output)
    if not disjoint(source, output):
        raise ValueError("failsafe output must be disjoint from input")
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
    count = errors = 0
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
                    errors += 1
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
            final, (submission_bytes(r) for r in rows()), allow_exclusive_fallback=True
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
                (exact_json(event) + "\n").encode("utf-8"),
                allow_exclusive_fallback=True,
            )
    outcome = {
        "valid": count > 0,
        "mode": "failsafe_all_abstain",
        "question_ids": count,
        "malformed_lines": errors,
        "primary_error": primary_error,
        "publication": publication,
        "gold_content_read": False,
    }
    publish(
        scratch / "diagnostics.json",
        (exact_json(outcome) + "\n").encode("utf-8"),
        allow_exclusive_fallback=True,
    )
    return outcome


def submission_predict(input_dir, output, *, config_path=None, started=None):
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
