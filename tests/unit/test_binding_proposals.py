import json

import pytest

from datamate.binding_proposals import make_case, validate_proposal


def case(**identity):
    return make_case(
        "source",
        "Order: mã đơn\nNet: tổng thanh toán gồm VAT",
        [{"id": "c0001", "label": "Order"}, {"id": "c0002", "label": "Net"}],
        None,
        dict(code_sha256="a" * 64, model_revision="b" * 40, rulebook_sha256="c" * 64)
        | identity,
    )


def test_valid_quote_and_columns_still_never_grant_capability():
    result = validate_proposal(
        json.dumps(
            dict(
                choice="headers",
                quote="Order: mã đơn",
                bindings=[dict(column="c0001", role="id", quote="Order: mã đơn")],
            )
        ),
        case(),
    )
    assert result["citation_valid"] and not result["capabilities_granted"]
    assert result["review_status"] == "pending_semantic_review"


@pytest.mark.parametrize(
    "change",
    [
        {"quote": "invented"},
        {"bindings": [dict(column="foreign", role="id", quote="mã đơn")]},
        {"bindings": [dict(column="c0001", role="id", quote="not in README")]},
        {"choice": "completed"},
    ],
)
def test_fabricated_quote_foreign_column_and_wrong_choice_are_rejected(change):
    value = dict(choice="headers", quote="mã đơn", bindings=[])
    with pytest.raises(ValueError):
        validate_proposal(json.dumps(value | change), case())


def test_unknown_requires_empty_claim_and_duplicate_json_keys_are_rejected():
    result = validate_proposal('{"choice":"unknown","quote":"","bindings":[]}', case())
    assert result["proposal"]["choice"] == "unknown"
    with pytest.raises(ValueError):
        validate_proposal(
            '{"choice":"headers","choice":"unknown","quote":"","bindings":[]}', case()
        )


def test_cache_key_changes_with_model_code_rulebook_or_content():
    initial = case()
    for field, value in [
        ("code_sha256", "d" * 64),
        ("model_revision", "e" * 40),
        ("rulebook_sha256", "f" * 64),
    ]:
        assert case(**{field: value})["id"] != initial["id"]
    assert (
        make_case(
            "source", "changed", initial["data"]["columns"], None, initial["identity"]
        )["id"]
        != initial["id"]
    )
