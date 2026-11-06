import json

import pytest

from datamate.intent_probe import (
    ContextProbeConfig,
    batch_schedule,
    intent_schema,
    make_case,
    project_descriptor,
    validate_intent,
)


def config(**changes):
    return (
        dict(
            profile="vuonghungnguyen07",
            workspace="vuonghungnguyen07",
            budget_usd=30.0,
            estimated_cost_usd=10.0,
            gpu="RTX-PRO-6000",
            memory_budget_bytes=32212254720,
            seed=0,
            max_model_len=8192,
            max_tokens=256,
            gpu_timeout_seconds=1200,
            startup_timeout_seconds=600,
            staging_timeout_seconds=300,
        )
        | changes
    )


def test_context_changes_do_not_relax_budget_or_identity():
    assert ContextProbeConfig.model_validate(config()).max_model_len == 8192
    assert (
        ContextProbeConfig.model_validate(config(max_model_len=4096)).max_model_len
        == 4096
    )
    for changes in [
        {"max_model_len": 16384},
        {"budget_usd": 31.0},
        {"profile": "other"},
    ]:
        with pytest.raises(ValueError):
            ContextProbeConfig.model_validate(config(**changes))


def test_descriptor_projection_excludes_raw_samples_and_paths():
    schema = {
        "business_id": "synthetic_b",
        "database": "C:/secret.duckdb",
        "tables": [
            {
                "sql_name": "raw_a",
                "source_name": "orders",
                "source_kind": "csv",
                "header_status": "resolved",
                "data_start_row": 2,
                "row_preview": ["secret"],
                "columns": [
                    {
                        "sql_name": "c0001",
                        "declared_name": "order_id",
                        "samples": ["secret"],
                        "header_cells": [{"value": "Order", "row": 1}],
                    }
                ],
            },
        ],
    }
    result = project_descriptor(schema)
    text = json.dumps(result)
    assert "secret" not in text and "synthetic_b" not in text
    assert "order_id" in text and "raw_a" in text
    assert result["source_strings_are_untrusted_data"] is True
    big = schema | {"tables": schema["tables"] * 20}
    assert project_descriptor(big)["omitted_tables"] == 8


def test_payload_allowlist_preserves_question_and_anchor():
    question = {
        "id": "synthetic_q",
        "business_id": "synthetic_b",
        "question": "Total this month?",
        "as_of_date": "2026-11-07",
    }
    case = make_case(question, {"tables": []})
    assert set(case) == {"id", "messages"}
    assert (
        json.loads(case["messages"][1]["content"])["question"] == question["question"]
    )
    with pytest.raises(ValueError):
        make_case(question | {"answer": 123}, {"tables": []})


def test_intent_parser_rejects_extra_fields_invalid_operation_and_repair():
    value = {
        "operation": "revenue_total",
        "period_text": "this month",
        "comparison_text": "",
        "filter_texts": [],
        "reason": "",
    }
    assert validate_intent(json.dumps(value)) == value
    assert intent_schema()["additionalProperties"] is False
    for bad in [
        value | {"answer": 123},
        value | {"operation": "sql"},
        value | {"filter_texts": [3]},
    ]:
        with pytest.raises(ValueError):
            validate_intent(json.dumps(bad))
    with pytest.raises(ValueError):
        validate_intent("```json\n" + json.dumps(value) + "\n```")


@pytest.mark.parametrize("size", [1, 2, 4])
def test_identical_workload_in_batch_schedule(size):
    batches = batch_schedule(4, size)
    assert [i for batch in batches for i in batch] == [0, 1, 2, 3]
    assert max(map(len, batches)) == size
