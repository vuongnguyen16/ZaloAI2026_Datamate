"""P2a CPU safety coordinator. Default backend abstains; no model or gold IO."""

import hashlib
import time
import uuid
from pathlib import Path

from datamate.bounded_execution import Deadline, run_bounded
from datamate.contracts import Question
from datamate.ingest.loader import disjoint
from datamate.prediction_store import RunStore, publish, regular_bytes, safe_path
from datamate.scoring import parse_object
from datamate.serialization import exact_json, format_submission, submission_bytes

DEFAULTS = {"budget_seconds": 21600, "reserve_seconds": 1, "per_question_seconds": 30}
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_LINE_BYTES = 1024 * 1024


def read_prediction_questions(path: Path):
    raw = regular_bytes(path, MAX_INPUT_BYTES, single_link=True)
    questions, rejected, errors, payloads = {}, {}, [], {}
    for index, line in enumerate(raw.splitlines(), 1):
        if index > 100000:
            raise ValueError("question line count exceeds budget")
        qid = None
        try:
            if len(line) > MAX_LINE_BYTES:
                raise ValueError("question line exceeds budget")
            obj = parse_object(
                line.removeprefix(b"\xef\xbb\xbf") if index == 1 else line
            )
            candidate = obj.get("id")
            if isinstance(candidate, str) and candidate.strip():
                candidate.encode("utf-8")
                qid = candidate
            if qid is None:
                raise ValueError("unrouteable question ID")
            canonical = exact_json(obj)
            if qid in payloads:
                if payloads[qid] != canonical:
                    questions.pop(qid, None)
                    rejected[qid] = "input_conflict"
                    errors.append({"kind": "input_conflict", "line": index})
                continue
            payloads[qid] = canonical
            if len(payloads) > 10000:
                raise ValueError("question ID count exceeds budget")
            questions[qid] = Question.model_validate(obj)
        except (ValueError, TypeError, UnicodeError):
            if len(payloads) > 10000:
                raise ValueError("question ID count exceeds budget")
            errors.append({"kind": "invalid_question", "line": index})
            if qid is not None:
                questions.pop(qid, None)
                rejected[qid] = "invalid_question"
    if not payloads:
        raise ValueError("no routeable question IDs")
    return questions, rejected, errors


def _digest(value):
    return hashlib.sha256(exact_json(value).encode("utf-8")).hexdigest()


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


def run_predict(input_dir: Path, output: Path, config=None, backend=None, started=None):
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
    code = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(Path(__file__).parent.glob("*.py"))
    }
    identity = {
        "schema_version": 1,
        "input_sha256": _digest(inventory),
        "config_sha256": _digest(settings),
        "code_sha256": _digest(code),
        "model_revision": "no_model"
        if backend is None
        else f"synthetic:{backend.__module__}.{backend.__qualname__}",
    }
    with RunStore(output, identity) as store:
        records = store.recover()
        if not set(records) <= set(ids):
            raise ValueError("checkpoint contains foreign question IDs")
        backend_failed = False
        for qid in ids:
            if qid in records:
                continue
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
                    backend_failed = True
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
            store.append(prediction.output())
            records[qid] = prediction.output()
        final = b"".join(submission_bytes(records[qid]) for qid in ids)
        publication = publish(output / "submission.jsonl", final)
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
            output / "execution.jsonl",
            b"".join((exact_json(e) + "\n").encode("utf-8") for e in logs),
        )
        publish(
            output / f"diagnostics-{uuid.uuid4().hex}.json",
            (
                exact_json({"input_errors": errors, "checkpoint_errors": store.errors})
                + "\n"
            ).encode("utf-8"),
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
        publish(output / "run.json", (exact_json(summary) + "\n").encode("utf-8"))
        return {
            **summary,
            "publication": publication,
            "checkpoint_error_count": len(store.errors),
        }
