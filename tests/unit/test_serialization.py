from decimal import Decimal

import pytest

from datamate.contracts import Submission
from datamate.scoring import parse_object, score
from datamate.serialization import format_submission, submission_bytes


@pytest.mark.parametrize(
    "kind,value,expected",
    [
        ("number", Decimal("1.0000000000000001"), b"1.0000000000000001"),
        ("number", 9007199254740993, b"9007199254740993"),
        ("number", Decimal("0.1"), b"0.1"),
        ("number", Decimal("1E+20"), b"100000000000000000000"),
        ("number", Decimal("-0.00"), b"0"),
        ("percent", Decimal("1.005"), b"1.01"),
        ("percent", Decimal("-1.005"), b"-1.01"),
    ],
)
def test_exact_final_bytes_survive_scorer_roundtrip(kind, value, expected):
    prediction = format_submission("synthetic", kind, value)
    raw = submission_bytes(prediction)
    assert b'"answer":' + expected in raw
    assert raw.endswith(b"\n") and b"E+" not in raw and b"e-" not in raw
    actual = parse_object(raw)
    reference = dict(id="synthetic", type=kind, answer=Decimal(expected.decode()))
    assert score(reference, actual)["score"] == 1


@pytest.mark.parametrize(
    "kind,value",
    [
        ("string", "0012"),
        ("date", "2026-11"),
        ("boolean", False),
        ("list", ["a", Decimal("1.0000000000000001")]),
        ("table", {"columns": ["a"], "rows": [[Decimal("0.1")]]}),
        ("unanswerable", None),
        ("abstain", None),
    ],
)
def test_all_other_types_remain_valid(kind, value):
    raw = submission_bytes(format_submission("synthetic", kind, value))
    actual = parse_object(raw)
    assert score(dict(id="synthetic", type=kind, answer=value), actual)["score"] == (
        0 if kind == "abstain" else 1
    )


@pytest.mark.parametrize(
    "kind,value",
    [
        ("number", True),
        ("number", Decimal("NaN")),
        ("number", Decimal("Infinity")),
        ("number", Decimal("1e1001")),
        ("number", "1.1"),
        ("table", {"columns": ["x"], "rows": [[None]]}),
        ("string", "\ud800"),
    ],
)
def test_format_rejection_is_explicit_abstain(kind, value):
    result = parse_object(submission_bytes(format_submission("synthetic", kind, value)))
    assert result == {"id": "synthetic", "type": "abstain", "reason": "format_rejected"}


def test_submission_accepts_decimal_without_relaxing_boolean_or_nonfinite():
    assert Submission(id="s", type="number", answer=Decimal("0.1")).answer == Decimal(
        "0.1"
    )
    for value in [True, Decimal("NaN"), Decimal("1e1001")]:
        with pytest.raises(ValueError):
            Submission(id="s", type="number", answer=value)


def test_legacy_writer_can_receive_decimal(tmp_path):
    from datamate.runner import write_results

    (tmp_path / "logs").mkdir()
    write_results(
        tmp_path, [Submission(id="s", type="number", answer=Decimal("0.1"))], []
    )
    assert parse_object((tmp_path / "submission.jsonl").read_bytes())[
        "answer"
    ] == Decimal("0.1")
