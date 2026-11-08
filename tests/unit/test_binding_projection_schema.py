import json

import pytest

from datamate.binding_proposals import make_case, validate_proposal
from datamate.proposal_evidence import combine_spans


def projected():
    spans = [
        dict(
            source="README.md",
            sha256="a" * 64,
            line_start=1,
            line_end=1,
            text="order id",
        ),
        dict(
            source="README.md",
            sha256="a" * 64,
            line_start=9,
            line_end=9,
            text="net amount",
        ),
    ]
    evidence, projection = combine_spans(spans, [dict(omitted=True)])
    return make_case(
        "source", evidence, [dict(id="c1", label="ID")], None, {}, projection=projection
    )


def test_cross_span_quote_rejected_and_omissions_in_prompt():
    case = projected()
    assert case["data"]["projection"]["omitted"]
    with pytest.raises(ValueError, match="citation"):
        validate_proposal(
            json.dumps(
                dict(choice="headers", quote=case["data"]["evidence"], bindings={})
            ),
            case,
        )


def test_column_keyed_binding_and_nonledger_role_only():
    case = projected()
    value = dict(
        choice="headers",
        quote="order id",
        bindings={"c1": dict(role="id", quote="order id")},
    )
    result = validate_proposal(json.dumps(value), case)
    assert result["proposal"]["bindings"][0]["column"] == "c1"
    assert not result["capabilities_granted"]
    with pytest.raises(ValueError, match="non-ledger"):
        validate_proposal(json.dumps(value | dict(choice="master")), case)
    duplicate = '{"choice":"headers","quote":"order id","bindings":{"c1":{"role":"id","quote":"order id"},"c1":{"role":"day","quote":"order id"}}}'
    with pytest.raises(ValueError):
        validate_proposal(duplicate, case)


def test_case_schema_only_allows_case_columns_and_choice_groups():
    from datamate.binding_proposals import proposal_schema

    schema = proposal_schema(projected())
    alternatives = schema["oneOf"]
    headers = next(
        x for x in alternatives if x["properties"]["choice"].get("const") == "headers"
    )
    assert set(headers["properties"]["bindings"]["properties"]) == {"c1"}
    assert headers["properties"]["bindings"]["additionalProperties"] is False
    master = next(
        x for x in alternatives if x["properties"]["choice"].get("const") == "master"
    )
    assert master["properties"]["bindings"]["maxProperties"] == 0


def test_binding_output_budget_is_separate_from_intent_probe():
    from datamate.binding_proposals import BindingProposalConfig
    from datamate.intent_probe import ContextProbeConfig

    assert BindingProposalConfig.model_fields["max_tokens"].default == 512
    assert any(
        getattr(x, "le", None) == 256
        for x in ContextProbeConfig.model_fields["max_tokens"].metadata
    )
