"""Strict CPU validation of P1 raw model evidence. No JSON repair or PA claim."""

import math

from datamate.contracts import Submission, json_object
from datamate.model_probe import MEMORY_BYTES

ANSWER_KINDS = {"number", "percent", "string", "date", "boolean", "list", "table"}


def evaluate_probe(cases: list[dict], rounds: list[dict], telemetry: dict) -> dict:
    expected = {case["id"]: case["expected"] for case in cases}
    errors = []
    normalized, valid_counts, correctness = [], [], []
    if len(cases) != 50 or len(expected) != 50 or len(rounds) != 2:
        errors.append("expected exactly 50 unique cases and two rounds")
    for index, run in enumerate(rounds):
        rows = run.get("records", [])
        seen, outputs, correct = set(), {}, {kind: 0 for kind in ANSWER_KINDS}
        for row in rows:
            identifier = row.get("id")
            try:
                if identifier not in expected or identifier in seen:
                    raise ValueError("unknown or duplicate correlation id")
                seen.add(identifier)
                parsed = Submission.model_validate(json_object(row["text"]))
                if parsed.id != identifier:
                    raise ValueError("output id mismatch")
                output = parsed.output()
                outputs[identifier] = output
                if output == expected[identifier] and output["type"] in ANSWER_KINDS:
                    correct[output["type"]] += 1
            except (ValueError, TypeError, KeyError):
                errors.append(f"round {index}: invalid output {identifier}")
        if len(rows) != 50 or len(outputs) != 50:
            errors.append(f"round {index}: requires 50/50 valid unique outputs")
        if run.get("exit_code") != 0 or run.get("cleaned_up") is not True:
            errors.append(f"round {index}: engine failed or cleanup unproven")
        peaks = [
            run.get(key)
            for key in (
                "peak_memory_bytes",
                "torch_peak_allocated_bytes",
                "torch_peak_reserved_bytes",
            )
        ]
        if (
            type(run.get("memory_sample_count")) is not int
            or run["memory_sample_count"] <= 0
            or any(
                type(value) not in (int, float)
                or not math.isfinite(value)
                or not 0 < value <= MEMORY_BYTES
                for value in peaks
            )
        ):
            errors.append(f"round {index}: memory evidence missing or exceeds budget")
        if not all(correct.values()):
            errors.append(f"round {index}: missing correct non-abstain answer type")
        normalized.append(outputs)
        valid_counts.append(len(outputs))
        correctness.append(correct)
    same = len(normalized) == 2 and normalized[0] == normalized[1]
    if not same:
        errors.append("normalized outputs differ")
    pids = [run.get("pid") for run in rounds]
    starts = [run.get("engine_started_at") for run in rounds]
    if (
        len(pids) != 2
        or any(type(pid) is not int or pid <= 0 for pid in pids)
        or len(set(pids)) != 2
    ):
        errors.append("two fresh subprocesses required")
    if any(not isinstance(stamp, (int, float)) or stamp <= 0 for stamp in starts):
        errors.append("engine start evidence missing")
    peak = telemetry.get("peak_memory_bytes")
    memory_ok = (
        type(peak) in (int, float)
        and math.isfinite(peak)
        and 0 < peak <= MEMORY_BYTES
        and telemetry.get("memory_sample_count", 0) > 0
    )
    required = (
        "network_blocked",
        "weights_read_only",
        "snapshot_verified",
        "runtime_pins_verified",
    )
    if (
        telemetry.get("transport") != "modal"
        or telemetry.get("device_capability") != [12, 0]
        or not all(telemetry.get(key) is True for key in required)
        or not memory_ok
    ):
        errors.append("physical offline/runtime/memory evidence incomplete")
    return {
        "g1_passed": not errors,
        "valid_counts": valid_counts,
        "normalized_equal": same,
        "synthetic_correct_counts": correctness,
        "normalized": normalized,
        "errors": errors,
        "pa": "not_evaluated",
        "scope": "P1 synthetic compatibility only; not B0 or BTC quality",
    }
