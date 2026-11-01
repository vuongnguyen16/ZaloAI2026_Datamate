import pytest
from pydantic import ValidationError

from datamate.contracts import Question, Submission


@pytest.mark.parametrize(
    "kind,value",
    [
        ("number", True),
        ("number", "12.35"),
        ("number", float("nan")),
        ("percent", float("inf")),
        ("boolean", 1),
        ("date", "2026-02-30"),
        ("list", [True]),
        ("table", {"columns": ["x"], "rows": [[1, 2]]}),
    ],
)
def test_type_value_mismatch_is_rejected(kind, value):
    with pytest.raises(ValidationError):
        Submission(id="fixture", type=kind, answer=value)


def test_month_and_abstain_shapes():
    assert (
        Submission(id="q", type="date", answer="2026-09").output()["answer"]
        == "2026-09"
    )
    assert Submission(id="q", type="abstain").output() == {"id": "q", "type": "abstain"}


def test_as_of_is_required_not_system_date():
    with pytest.raises(ValidationError):
        Question(id="q", business_id="synthetic", question="hôm nay?")
