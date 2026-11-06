import copy
import json

import pytest


def cases():
    values = [
        ("number", 12.35),
        ("percent", 25.0),
        ("string", "0012"),
        ("date", "2026-02-01"),
        ("boolean", True),
        ("list", ["A", 1]),
        ("table", {"columns": ["x"], "rows": [[1]]}),
        ("unanswerable", None),
        ("abstain", None),
    ]
    result = []
    for i in range(50):
        kind, value = values[i % 9]
        expected = {"id": f"probe-{i}", "type": kind}
        if value is not None:
            expected["answer"] = copy.deepcopy(value)
        result.append(
            {"id": f"probe-{i}", "prompt": "Synthetic only", "expected": expected}
        )
    return result


def rounds():
    return [
        {
            "pid": pid,
            "engine_started_at": float(pid),
            "exit_code": 0,
            "cleaned_up": True,
            "records": [
                {"id": c["id"], "text": json.dumps(c["expected"]), "token_ids": [1, 2]}
                for c in cases()
            ],
        }
        for pid in (101, 102)
    ]


def telemetry():
    return {
        "transport": "modal",
        "device_capability": [12, 0],
        "network_blocked": True,
        "weights_read_only": True,
        "snapshot_verified": True,
        "runtime_pins_verified": True,
        "peak_memory_bytes": 29 * 1024**3,
        "memory_sample_count": 12,
    }


def evaluate(rs=None, tm=None):
    from datamate.probe_results import evaluate_probe

    return evaluate_probe(
        cases(),
        rs if rs is not None else rounds(),
        tm if tm is not None else telemetry(),
    )


def test_fixture_has_50_unique_self_contained_cases_and_never_sends_expected():
    from datamate.probe_fixtures import build_cases, inference_cases

    fixture = build_cases()
    assert len(fixture) == len({c["id"] for c in fixture}) == 50
    assert {c["expected"]["type"] for c in fixture} == {
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
    assert fixture[0]["expected"]["answer"] == 12.35
    assert fixture[2]["expected"]["answer"] == "0002"
    assert all(set(c) == {"id", "prompt"} for c in inference_cases(fixture))
    assert any("Tính" in c["prompt"] for c in fixture)


def test_success_requires_two_fresh_engines_and_all_json_valid():
    report = evaluate()
    assert report["g1_passed"] is True
    assert report["valid_counts"] == [50, 50]
    assert report["normalized_equal"] is True
    assert report["pa"] == "not_evaluated"


@pytest.mark.parametrize(
    "text",
    [
        "```json\n{}\n```",
        '{"id":"x","id":"y","type":"abstain"}',
        '{"id":"probe-0","type":"number","answer":NaN}',
        '{"id":"probe-0","type":"boolean","answer":1}',
        '{"id":"wrong-id","type":"abstain"}',
    ],
)
def test_malformed_or_mismatched_output_cannot_be_repaired_into_pass(text):
    rs = rounds()
    rs[0]["records"][0]["text"] = text
    report = evaluate(rs)
    assert report["g1_passed"] is False
    assert report["valid_counts"] == [49, 50]


@pytest.mark.parametrize(
    "failure", ["missing", "duplicate", "reused_pid", "failed_process", "unclean"]
)
def test_incomplete_or_nonindependent_run_fails(failure):
    rs = rounds()
    if failure == "missing":
        rs[0]["records"].pop()
    elif failure == "duplicate":
        rs[0]["records"][-1] = rs[0]["records"][0]
    elif failure == "reused_pid":
        rs[1]["pid"] = rs[0]["pid"]
    elif failure == "failed_process":
        rs[1]["exit_code"] = 1
    else:
        rs[0]["cleaned_up"] = False
    assert evaluate(rs)["g1_passed"] is False


@pytest.mark.parametrize(
    "change",
    [
        {"transport": "fake"},
        {"device_capability": [9, 0]},
        {"network_blocked": False},
        {"weights_read_only": False},
        {"snapshot_verified": False},
        {"runtime_pins_verified": False},
        {"peak_memory_bytes": None},
        {"peak_memory_bytes": 31 * 1024**3},
        {"peak_memory_bytes": 0},
        {"memory_sample_count": 0},
    ],
)
def test_fake_or_missing_physical_evidence_never_passes_g1(change):
    assert evaluate(tm=telemetry() | change)["g1_passed"] is False


def test_normalized_difference_is_reported_even_when_json_valid():
    rs = rounds()
    rs[1]["records"][0]["text"] = '{"id":"probe-0","type":"number","answer":999}'
    report = evaluate(rs)
    assert report["valid_counts"] == [50, 50]
    assert report["normalized_equal"] is False
    assert report["g1_passed"] is False


def test_all_abstain_does_not_pass_as_model_evidence():
    rs = rounds()
    for r in rs:
        for row in r["records"]:
            row["text"] = json.dumps({"id": row["id"], "type": "abstain"})
    report = evaluate(rs)
    assert report["valid_counts"] == [50, 50]
    assert report["g1_passed"] is False
