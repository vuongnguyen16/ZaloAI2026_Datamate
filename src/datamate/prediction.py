"""P2a CPU safety coordinator. Default backend abstains; no model or gold IO."""

import hashlib
import time
import uuid
from pathlib import Path

from datamate.bounded_execution import Deadline, run_bounded
from datamate.contracts import Question
from datamate.json_routing import project_id
from datamate.prediction_store import (
    RunStore,
    publish,
    publish_chunks,
    regular_bytes,
    safe_path,
)
from datamate.runtime_paths import disjoint, ignored_output_entries
from datamate.runtime_paths import output_layout as _output_layout
from datamate.scoring import parse_object
from datamate.serialization import exact_json, format_submission, submission_bytes

DEFAULTS = {"budget_seconds": 21600, "reserve_seconds": 120, "per_question_seconds": 30}
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_LINE_BYTES = 1024 * 1024
MAX_OUTPUT_BYTES = 128 * 1024 * 1024


def read_prediction_questions(path: Path):
    raw = regular_bytes(path, MAX_INPUT_BYTES, single_link=True)
    questions, rejected, errors, payloads, seen = {}, {}, [], {}, set()
    for index, line in enumerate(raw.splitlines(), 1):
        if index > 100000:
            raise ValueError("question line count exceeds budget")
        qid = None
        try:
            if len(line) > MAX_LINE_BYTES:
                raise ValueError("question line exceeds budget")
            line = line.removeprefix(b"\xef\xbb\xbf") if index == 1 else line
            candidate = project_id(line)
            candidate.encode("utf-8")
            qid = candidate
            seen.add(qid)
            if len(seen) > 10000:
                raise ValueError("question ID count exceeds budget")
            obj = parse_object(line.decode("utf-8"))
            question = Question.model_validate(obj)
            canonical = exact_json(question.model_dump())
            if qid in payloads:
                if payloads[qid] != canonical:
                    questions.pop(qid, None)
                    rejected[qid] = "input_conflict"
                    errors.append({"kind": "input_conflict", "line": index})
                continue
            payloads[qid] = canonical
            if qid not in rejected:
                questions[qid] = question
        except (ValueError, TypeError, UnicodeError, ArithmeticError, RecursionError):
            if len(seen) > 10000:
                raise ValueError("question ID count exceeds budget")
            errors.append({"kind": "invalid_question", "line": index})
            if qid is not None:
                questions.pop(qid, None)
                rejected[qid] = "invalid_question"
    if not seen:
        raise ValueError("no routeable question IDs")
    return questions, rejected, errors


def _digest(value):
    return hashlib.sha256(exact_json(value).encode("utf-8")).hexdigest()


def code_fingerprint(root=None):
    root = Path(__file__).parent if root is None else Path(root)
    return _digest(
        {
            p.relative_to(root).as_posix(): hashlib.sha256(
                safe_path(p).read_bytes()
            ).hexdigest()
            for p in sorted(root.rglob("*.py"))
        }
    )


def _inventory(root):
    # Only inference paths. In particular, never open answers.jsonl at split root.
    paths = [root / "questions.jsonl"]
    paths += [
        root / name
        for name in ("rulebook.md", "calendar.csv")
        if (root / name).exists()
    ]
    data = root / "data"
    if data.exists():
        safe_path(data)
        for path in data.rglob("*"):
            safe_path(path)
            if path.is_file():
                paths.append(path)
    if len(paths) > 10000:
        raise ValueError("input file count exceeds budget")
    result = {}
    total = 0
    for path in sorted(paths):
        safe_path(path)
        if path.stat().st_nlink != 1:
            raise ValueError("linked inference input")
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while block := handle.read(1024 * 1024):
                total += len(block)
                if total > 4 * 1024**3:
                    raise ValueError("input byte inventory exceeds budget")
                digest.update(block)
        result[str(path.relative_to(root)).replace("\\", "/")] = digest.hexdigest()
    return result


def _question_logs(
    logs, ids, records, identity, durations, *, allow_exclusive_fallback=False
):
    logs.mkdir(parents=True, exist_ok=True)
    identity_sha = _digest(identity)
    for index, qid in enumerate(ids):
        path = logs / f"{index:06d}.json"
        if path.exists():
            old = parse_object(regular_bytes(path))
            if (
                old.get("question_id") == qid
                and old.get("identity_sha256") == identity_sha
                and submission_bytes(old.get("answer", {}))
                == submission_bytes(records[qid])
            ):
                continue
        event = {
            "question_id": qid,
            "stage": "prediction_safety",
            "status": "abstain" if records[qid]["type"] == "abstain" else "answered",
            "answer": records[qid],
            "reason": records[qid].get("reason"),
            "duration_seconds": durations.get(qid, 0),
            "timing_available": qid in durations,
            "identity_sha256": identity_sha,
            "backend": identity["model_revision"],
            "evidence": "P2a CPU safety coordinator; no model inference. Replayed timing is unavailable when timing_available=false.",
        }
        publish(
            path,
            (exact_json(event) + "\n").encode("utf-8"),
            allow_exclusive_fallback=allow_exclusive_fallback,
        )


def run_predict(
    input_dir: Path,
    output: Path,
    config=None,
    backend=None,
    started=None,
    *,
    allow_exclusive_fallback=False,
):
    started = time.monotonic() if started is None else started
    settings = {**DEFAULTS, **(config or {})}
    if set(settings) != set(DEFAULTS) or any(
        type(v) not in (int, float) or not 0 < v <= 21600 for v in settings.values()
    ):
        raise ValueError("invalid prediction config")
    clock = Deadline(started, settings["budget_seconds"], settings["reserve_seconds"])
    root, output = safe_path(input_dir), safe_path(output)
    if not disjoint(root, output):
        raise ValueError("input and output must be disjoint")
    state_dir = _output_layout(output)
    ignored_entries = ignored_output_entries(output)
    inventory = _inventory(root)
    questions, rejected, errors = read_prediction_questions(root / "questions.jsonl")
    # Detect mutation during parsing; no checkpoint may be resumed under stale bytes.
    if (
        hashlib.sha256(
            regular_bytes(root / "questions.jsonl", MAX_INPUT_BYTES)
        ).hexdigest()
        != inventory["questions.jsonl"]
    ):
        raise ValueError("questions changed during inventory")
    ids = sorted(set(questions) | set(rejected))
    identity = {
        "schema_version": 1,
        "input_sha256": _digest(inventory),
        "config_sha256": _digest(settings),
        "code_sha256": code_fingerprint(),
        "model_revision": "no_model"
        if backend is None
        else f"synthetic:{backend.__module__}.{backend.__qualname__}",
    }
    with RunStore(
        state_dir, identity, allow_exclusive_fallback=allow_exclusive_fallback
    ) as store:
        records = store.recover()
        if not set(records) <= set(ids):
            raise ValueError("checkpoint contains foreign question IDs")
        backend_failed = False
        durations = {}
        retained = sum(len(submission_bytes(r)) for r in records.values())
        reserve_sizes = {
            qid: len(
                submission_bytes(
                    format_submission(qid, "abstain", reason="backend_unavailable")
                )
            )
            for qid in ids
            if qid not in records
        }
        reserve = sum(reserve_sizes.values())
        if retained + reserve > MAX_OUTPUT_BYTES:
            raise ValueError("recovered output exceeds byte budget")
        for qid in ids:
            if qid in records:
                continue
            question_started = time.monotonic()
            reason = rejected.get(qid)
            candidate = None
            if reason is None and clock.work_remaining <= 0:
                reason = "deadline"
            if reason is None and backend_failed:
                reason = "backend_unavailable"
            if reason is None and backend is None:
                reason = "no_model"
            if reason is None:
                # P2a bounded batch size is one; real resident model adapters are P2b/P3.
                try:
                    result = run_bounded(
                        backend,
                        (questions[qid].model_dump(),),
                        min(clock.work_remaining, settings["per_question_seconds"]),
                    )
                except Exception as exc:
                    result = {"status": "startup_error", "error": type(exc).__name__}
                if result["status"] != "ok":
                    reason = "backend_" + result["status"]
                    backend_failed = (
                        result["status"] == "startup_error"
                        or result.get("error")
                        in {"worker_exited", "invalid_worker_result"}
                    )
                else:
                    candidate = result["value"]
            if reason:
                prediction = format_submission(qid, "abstain", reason=reason)
            elif isinstance(candidate, dict) and candidate.get("id", qid) == qid:
                prediction = format_submission(
                    qid,
                    candidate.get("type"),
                    candidate.get("answer"),
                    candidate.get("reason"),
                )
            else:
                prediction = format_submission(qid, "abstain", reason="format_rejected")
            reserve -= reserve_sizes[qid]
            if (
                retained + len(submission_bytes(prediction)) + reserve
                > MAX_OUTPUT_BYTES
            ):
                prediction = format_submission(qid, "abstain", reason="output_budget")
                backend_failed = True
            store.append(prediction.output())
            durations[qid] = time.monotonic() - question_started
            records[qid] = prediction.output()
            retained += len(submission_bytes(prediction))
        publication = publish_chunks(
            output / "submission.jsonl",
            (submission_bytes(records[qid]) for qid in ids),
            MAX_OUTPUT_BYTES,
            allow_exclusive_fallback=allow_exclusive_fallback,
        )
        _question_logs(
            output / "logs" / f"submission-{publication['sha256']}",
            ids,
            records,
            identity,
            durations,
            allow_exclusive_fallback=allow_exclusive_fallback,
        )
        logs = [
            {
                "id": qid,
                "type": records[qid]["type"],
                "reason": records[qid].get("reason"),
                "backend": identity["model_revision"],
            }
            for qid in ids
        ]
        publish(
            state_dir / "execution.jsonl",
            b"".join((exact_json(e) + "\n").encode("utf-8") for e in logs),
            allow_exclusive_fallback=allow_exclusive_fallback,
        )
        publish(
            state_dir / f"diagnostics-{uuid.uuid4().hex}.json",
            (
                exact_json(
                    {
                        "input_errors": errors,
                        "checkpoint_errors": store.errors,
                        "publication": publication,
                        "ignored_output_entries": ignored_entries,
                    }
                )
                + "\n"
            ).encode("utf-8"),
            allow_exclusive_fallback=allow_exclusive_fallback,
        )
        summary = {
            "valid": True,
            "scope": "cpu_safety_only_not_B0_or_G2",
            "backend": "no_model" if backend is None else "synthetic_callable",
            "question_ids": len(ids),
            "data_error_count": len(errors),
            "gold_content_read": False,
            "identity": identity,
        }
        publish(
            state_dir / "run.json",
            (exact_json(summary) + "\n").encode("utf-8"),
            allow_exclusive_fallback=allow_exclusive_fallback,
        )
        return {
            **summary,
            "publication": publication,
            "checkpoint_error_count": len(store.errors),
        }
