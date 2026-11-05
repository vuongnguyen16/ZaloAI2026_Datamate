from decimal import Decimal

import pytest

from datamate.scoring import parse_object, score


def entry(kind, answer=None, **extra):
    return dict(id="synthetic", type=kind, answer=answer, **extra)


@pytest.mark.parametrize(
    "reference,prediction,expected",
    [
        (entry("number", 12), entry("number", 12.0), 1),
        (entry("number", Decimal("1.23")), entry("number", Decimal("1.234")), -1),
        (entry("number", 1), entry("number", True), -1),
        (entry("number", 2**60), entry("number", 2**60 + 1), -1),
        (entry("percent", Decimal("1.24")), entry("percent", Decimal("1.235")), 1),
        (entry("percent", Decimal("-1.24")), entry("percent", Decimal("-1.235")), 1),
        (entry("percent", 12), entry("percent", -12), -1),
        (entry("percent", 0), entry("percent", Decimal("-0.001")), 1),
        (entry("string", "Cà phê sữa"), entry("string", " CÀ-PHÊ—sữa! "), 1),
        (entry("string", "Cà phê sữa"), entry("string", "ca phe sua"), -1),
        (entry("string", "Cà phê", alias=["SP0042"]), entry("string", "sp0042"), 1),
        (entry("string", "Straße"), entry("string", "strasse"), -1),
        (entry("string", "á"), entry("string", "a\u0301"), 1),
        (entry("date", "2026-08-15"), entry("date", "2026-08-15"), 1),
        (entry("date", "2025-09"), entry("date", "2025-09-01"), -1),
        (entry("date", "2026-02-28"), entry("date", "2026-02-30"), -1),
        (entry("boolean", True), entry("boolean", True), 1),
        (entry("boolean", True), entry("boolean", 1), -1),
        (entry("boolean", True), entry("boolean", False), -1),
        (entry("list", ["Cà phê", 2]), entry("list", ["cà-phê", 2.0]), 1),
        (entry("list", ["a", "b"]), entry("list", ["b", "a"]), -1),
        (entry("list", [2]), entry("list", ["2"]), -1),
        (entry("list", [2]), entry("list", [None]), -1),
        (entry("unanswerable"), entry("unanswerable"), 1),
        (entry("number", 0), entry("unanswerable"), -1),
        (entry("unanswerable"), entry("number", 0), -1),
        (entry("number", 1), entry("abstain"), 0),
        (entry("number", 1), entry("abstain", "extra payload"), 0),
        (entry("number", 1), None, 0),
        (entry("number", 1), dict(id="synthetic", type=[]), -1),
        (entry("number", 1), entry("string", "1"), -1),
    ],
)
def test_written_matching_rules_and_provisional_corners(
    reference, prediction, expected
):
    assert score(reference, prediction)["score"] == expected


def test_table_reorders_named_columns_and_rows_and_uses_set_semantics():
    gold = entry(
        "table",
        {
            "columns": ["Tên khách", "Số tiền"],
            "rows": [["Chị Lan", 10], ["Anh Tú", 20], ["Anh Tú", 20]],
        },
    )
    pred = entry(
        "table",
        {
            "columns": ["số-tiền", "TÊN KHÁCH"],
            "rows": [[20, "anh tú"], [10, "chị lan"]],
        },
    )
    assert score(gold, pred)["score"] == 1
    pred["answer"]["rows"][0][0] = 21
    assert score(gold, pred)["score"] == -1


def test_table_positional_fallback_duplicate_names_and_null_rejection():
    gold = entry("table", {"columns": ["name", "total"], "rows": [["A", 2]]})
    assert (
        score(
            gold, entry("table", {"columns": ["renamed", "other"], "rows": [["a", 2]]})
        )["score"]
        == 1
    )
    assert (
        score(gold, entry("table", {"columns": ["name", "name"], "rows": [["a", 2]]}))[
            "score"
        ]
        == 1
    )
    assert (
        score(
            gold, entry("table", {"columns": ["name", "total"], "rows": [["a", None]]})
        )["score"]
        == -1
    )


def test_decimal_parser_preserves_precision_and_rejects_ambiguous_json():
    obj = parse_object('{"id":"synthetic","type":"number","answer":1.0000000000000001}')
    assert score(entry("number", 1), obj)["score"] == -1
    for raw in ['{"id":"a","id":"b"}', '{"answer":NaN}', '{"answer":Infinity}']:
        with pytest.raises(ValueError):
            parse_object(raw)


def test_nested_list_aliases_are_position_bound():
    gold = entry("list", ["Product A", "Product B"], alias=[["P001"], ["P002"]])
    assert score(gold, entry("list", ["p001", "p002"]))["score"] == 1
    assert score(gold, entry("list", ["p002", "p001"]))["score"] == -1
    assert (
        score(entry("list", [1, 2], alias=[[], []]), entry("list", [1, 2]))["score"]
        == 1
    )


def test_table_aliases_match_rows_bijectively_after_column_alignment():
    gold = entry(
        "table",
        dict(columns=["Product", "Qty"], rows=[["Product A", 5], ["Product B", 5]]),
        alias=[["P001", "shared"], ["P002", "shared"]],
    )
    assert (
        score(
            gold,
            entry(
                "table",
                dict(columns=["Qty", "Product"], rows=[[5, "P002"], [5, "P001"]]),
            ),
        )["score"]
        == 1
    )
    assert (
        score(
            gold, entry("table", dict(columns=["Product", "Qty"], rows=[["shared", 5]]))
        )["score"]
        == -1
    )


def test_ambiguous_nested_alias_shapes_fail_reference_validation():
    with pytest.raises(ValueError):
        score(entry("list", ["A", "B"], alias=[["X"]]), entry("abstain"))
    with pytest.raises(ValueError):
        score(
            entry("table", dict(columns=["a", "b"], rows=[["A", "B"]]), alias=[["X"]]),
            entry("abstain"),
        )
