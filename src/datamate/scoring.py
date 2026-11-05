"""Deterministic matching from the supplied written rules; no model or gold IO."""

import json
import math
import re
import unicodedata
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext

TYPES = {
    "number",
    "percent",
    "string",
    "date",
    "boolean",
    "list",
    "table",
    "unanswerable",
    "abstain",
}


def parse_object(raw: bytes | str) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def reject(_):
        raise ValueError("Non-finite JSON number")

    try:
        obj = json.loads(
            raw, parse_float=Decimal, object_pairs_hook=pairs, parse_constant=reject
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("Invalid JSON object") from exc
    if not isinstance(obj, dict):
        raise ValueError("JSON record must be an object")
    return obj


def number(value) -> Decimal:
    if type(value) not in (int, float, Decimal) or (
        type(value) is float and not math.isfinite(value)
    ):
        raise ValueError("Expected finite numeric value, excluding boolean")
    result = Decimal(str(value))
    if (
        not result.is_finite()
        or len(result.as_tuple().digits) > 256
        or abs(result.adjusted()) > 1000
    ):
        raise ValueError("Number exceeds matching bounds")
    return result


def normalize_string(value: str) -> str:
    text = unicodedata.normalize("NFC", value).lower()
    return " ".join(
        "".join(c if c.isalnum() or c.isspace() else " " for c in text).split()
    )


def validate_cell(value) -> None:
    if not isinstance(value, str):
        number(value)


def validate_entry(obj: dict, *, reference=False) -> dict:
    allowed = {"id", "type", "answer", "reason"} | ({"alias"} if reference else set())
    if (
        not set(obj) <= allowed
        or not isinstance(obj.get("id"), str)
        or not obj["id"].strip()
        or not isinstance(obj.get("type"), str)
        or obj.get("type") not in TYPES
    ):
        raise ValueError("Invalid answer envelope")
    kind, value = obj["type"], obj.get("answer")
    if (
        "reason" in obj
        and obj["reason"] is not None
        and not isinstance(obj["reason"], str)
    ):
        raise ValueError("Invalid reason")
    if kind not in {"abstain", "unanswerable"} and "answer" not in obj:
        raise ValueError("Missing answer")
    if kind in {"number", "percent"}:
        number(value)
    elif kind == "string":
        if not isinstance(value, str):
            raise ValueError("String answer required")
    elif kind == "date":
        if not isinstance(value, str) or not re.fullmatch(
            r"\d{4}-\d{2}(-\d{2})?", value
        ):
            raise ValueError("ISO date/month required")
        date.fromisoformat(value if len(value) == 10 else value + "-01")
    elif kind == "boolean":
        if type(value) is not bool:
            raise ValueError("Strict boolean required")
    elif kind == "list":
        if not isinstance(value, list) or len(value) > 10000:
            raise ValueError("Bounded list required")
        for cell in value:
            validate_cell(cell)
    elif kind == "table":
        if (
            not isinstance(value, dict)
            or set(value) != {"columns", "rows"}
            or not isinstance(value["columns"], list)
            or not isinstance(value["rows"], list)
            or len(value["columns"]) > 256
            or len(value["rows"]) > 10000
            or not all(isinstance(c, str) for c in value["columns"])
        ):
            raise ValueError("Invalid bounded table")
        for row in value["rows"]:
            if not isinstance(row, list) or len(row) != len(value["columns"]):
                raise ValueError("Invalid table row width")
            for cell in row:
                validate_cell(cell)
    elif value is not None:
        raise ValueError("No answer value allowed for abstain/unanswerable")
    if reference:
        aliases = obj.get("alias", [])
        if aliases is None:
            aliases = []
        if not isinstance(aliases, list):
            raise ValueError("Unsupported reference alias shape")
        if aliases:
            if kind == "string":
                if not all(isinstance(a, str) for a in aliases):
                    raise ValueError("Scalar string aliases must be strings")
            elif kind in {"list", "table"}:
                items = value if kind == "list" else value["rows"]
                if len(aliases) != len(items) or not all(
                    isinstance(a, list) and all(isinstance(s, str) for s in a)
                    for a in aliases
                ):
                    raise ValueError(
                        "Nested aliases must align with list items/table rows"
                    )
                if kind == "table" and (
                    len(items) > 256
                    or any(
                        not row
                        or not isinstance(row[0], str)
                        or any(isinstance(v, str) for v in row[1:])
                        for row in items
                    )
                ):
                    raise ValueError(
                        "Table row aliases require one leading text cell, within 256 rows"
                    )
                if kind == "list" and any(
                    a and not isinstance(v, str) for a, v in zip(aliases, items)
                ):
                    raise ValueError("Numeric list items cannot have string aliases")
            else:
                raise ValueError("Aliases unsupported for this reference type")
    return obj


def canonical_cell(value):
    return (
        ("string", normalize_string(value))
        if isinstance(value, str)
        else ("number", number(value))
    )


def cell_match(actual, expected, aliases=()) -> bool:
    if isinstance(actual, str) and isinstance(expected, str):
        return normalize_string(actual) in {
            normalize_string(s) for s in [expected, *aliases]
        }
    return canonical_cell(actual) == canonical_cell(expected)


def table_match(actual: dict, expected: dict, aliases=()) -> bool:
    if len(actual["columns"]) != len(expected["columns"]):
        return False
    ac = [normalize_string(c) for c in actual["columns"]]
    ec = [normalize_string(c) for c in expected["columns"]]
    order = list(range(len(ac)))
    if (
        all(ac)
        and all(ec)
        and len(set(ac)) == len(ac)
        and len(set(ec)) == len(ec)
        and set(ac) == set(ec)
    ):
        order = [ac.index(c) for c in ec]
    left = {tuple(canonical_cell(row[i]) for i in order) for row in actual["rows"]}
    right = {tuple(canonical_cell(cell) for cell in row) for row in expected["rows"]}
    if left == right or not aliases:
        return left == right
    if len(left) != len(right):
        return False
    reference_aliases = {}
    for row, alias in zip(expected["rows"], aliases):
        key = tuple(canonical_cell(cell) for cell in row)
        reference_aliases.setdefault(key, set()).update(
            normalize_string(s) for s in [row[0], *alias]
        )
    expected_rows = list(reference_aliases)
    adjacency = [
        [
            i
            for i, row in enumerate(expected_rows)
            if candidate[1:] == row[1:]
            and candidate[0][0] == "string"
            and candidate[0][1] in reference_aliases[row]
        ]
        for candidate in left
    ]
    matched = {}

    def augment(index, seen):
        for ref in adjacency[index]:
            if ref not in seen:
                seen.add(ref)
                if ref not in matched or augment(matched[ref], seen):
                    matched[ref] = index
                    return True
        return False

    return all(augment(i, set()) for i in range(len(adjacency)))


def percent(value) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 1100
        return number(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def score(reference: dict, prediction: dict | None) -> dict:
    validate_entry(reference, reference=True)
    if prediction is None:
        return dict(status="abstain", score=0, reason="missing_prediction")
    if prediction.get("id") != reference["id"]:
        raise ValueError("Prediction/reference ID mismatch")
    # The written rule says abstain is always zero, irrespective of payload.
    if prediction.get("type") == "abstain":
        return dict(status="abstain", score=0, reason="explicit_abstain")
    try:
        validate_entry(prediction)
    except (ValueError, InvalidOperation):
        return dict(status="wrong", score=-1, reason="invalid_answer_shape")
    if prediction["type"] != reference["type"]:
        return dict(status="wrong", score=-1, reason="type_mismatch")
    kind = reference["type"]
    a, e = prediction.get("answer"), reference.get("answer")
    if kind == "string":
        matched = normalize_string(a) in {
            normalize_string(s) for s in [e, *(reference.get("alias") or [])]
        }
    elif kind == "number":
        matched = number(a) == number(e)
    elif kind == "percent":
        matched = percent(a) == percent(e)
    elif kind in {"date", "boolean"}:
        matched = a == e
    elif kind == "list":
        aliases = reference.get("alias") or [[] for _ in e]
        matched = len(a) == len(e) and all(
            cell_match(x, y, alias) for x, y, alias in zip(a, e, aliases)
        )
    elif kind == "table":
        matched = table_match(a, e, reference.get("alias") or [])
    else:
        matched = kind == "unanswerable"
    return dict(
        status="correct" if matched else "wrong",
        score=1 if matched else -1,
        reason="matched" if matched else "value_mismatch",
    )


def validate_policy(policy: dict) -> None:
    if (
        policy.get("version") != 1
        or policy.get("number") != "decimal_exact_no_prediction_rounding"
        or policy.get("percent")
        != {"places": 2, "rounding": "ROUND_HALF_UP", "signed_zero": "equivalent"}
        or policy.get("table")
        != {
            "columns": "unique_full_name_mapping_else_position",
            "rows": "set",
            "null_cells": "unsupported",
        }
        or policy.get("aliases")
        != "scalar_string_or_positional_list_or_table_leading_text_by_row"
        or policy.get("string") != "NFC_lower_non_alnum_to_space_collapse_keep_accents"
        or policy.get("date") != "strict_ISO_exact"
        or policy.get("boolean") != "strict_bool"
        or policy.get("list") != "ordered_cell_match"
        or policy.get("missing") != "abstain"
        or policy.get("abstain") != "always_zero_including_extra_payload"
        or policy.get("invalid_answer_with_known_id") != "wrong"
    ):
        raise ValueError("Unsupported or weakened scoring policy")
