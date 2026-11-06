"""Exact, bounded prediction JSON. This module never reads reference answers."""

import json
from decimal import Decimal

from datamate.contracts import Submission
from datamate.scoring import number, parse_object, percent, validate_entry

MAX_RECORD_BYTES = 4 * 1024 * 1024


def exact_json(value, depth=0) -> str:
    if depth > 16:
        raise ValueError("JSON nesting exceeds budget")
    if value is None or type(value) in (bool, str):
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    if type(value) in (int, float, Decimal):
        numeric = number(value)
        return "0" if numeric.is_zero() else format(numeric, "f")
    if isinstance(value, list):
        return "[" + ",".join(exact_json(v, depth + 1) for v in value) + "]"
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        return (
            "{"
            + ",".join(
                exact_json(k, depth + 1) + ":" + exact_json(v, depth + 1)
                for k, v in value.items()
            )
            + "}"
        )
    raise ValueError("Unsupported JSON value")


def submission_bytes(value: Submission | dict) -> bytes:
    obj = value.output() if isinstance(value, Submission) else value
    # Validate before encoding too, so large containers are rejected early.
    validate_entry(obj)
    raw = (exact_json(Submission.model_validate(obj).output()) + "\n").encode("utf-8")
    if len(raw) > MAX_RECORD_BYTES:
        raise ValueError("Prediction record exceeds byte budget")
    validate_entry(parse_object(raw))
    return raw


def format_submission(qid, kind, answer=None, reason=None) -> Submission:
    # An invalid ID cannot be repaired by inventing one.
    fallback = Submission(id=qid, type="abstain", reason="format_rejected")
    submission_bytes(fallback)
    try:
        if kind == "percent":
            answer = percent(answer)
        candidate = Submission(id=qid, type=kind, answer=answer, reason=reason)
        submission_bytes(candidate)
        return candidate
    except (ValueError, TypeError, ArithmeticError, UnicodeError):
        return fallback
