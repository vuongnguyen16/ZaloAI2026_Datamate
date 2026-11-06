from datetime import date
from decimal import Decimal

import pytest

from datamate.domain_lib.metrics import order_count, revenue_total
from datamate.domain_lib.model import DomainAbstain, Period
from datamate.domain_lib.orders import (
    Binding,
    BoundSource,
    EntityBinding,
    Filter,
    RawRow,
    adapt_sources,
)


def bind(
    rows, *, role="lines", unit="synthetic_lines", entities=None, amount="net", **kwargs
):
    binding = Binding(
        role=role,
        order_id="id",
        placed_at="day",
        status="status",
        amount=amount if role == "lines" else None,
        status_values={
            "ok": "completed",
            "ship": "shipping",
            "cancel": "cancelled",
            "return": "returned",
        },
        entities=entities or {},
        **kwargs,
    )
    return BoundSource(
        unit, "0" * 64, binding, [RawRow(i + 1, r) for i, r in enumerate(rows)]
    )


def r(qid, amount="100", status="ok", day="2026-11-01", **extra):
    return dict(id=qid, day=day, status=status, net=amount, **extra)


NOV = Period(date(2026, 11, 1), date(2026, 11, 30))


def test_grain_status_line_discounts_vat_ship_and_service_fee():
    rows = [
        r("A", "90", vat="10", ship_fee="20", shop_voucher="50"),
        r("A", "30", vat="3", ship_fee="20", shop_voucher="50"),
        r("B", "40", "ship"),
        r("C", "999", "cancel"),
        r("D", "999", "return"),
        r("E", "5", label="Phí phục vụ"),
    ]
    book = adapt_sources([bind(rows)])
    assert revenue_total(book, NOV) == Decimal(165)
    assert order_count(book, NOV) == 3


def test_partial_future_return_excludes_entire_order_before_period_filter():
    lines = bind([r("A"), r("A", "50"), r("B", "10")])
    events = bind(
        [r("A", "-1", "return", "2027-01-01")], role="events", unit="synthetic_returns"
    )
    book = adapt_sources([lines, events])
    assert revenue_total(book, NOV) == 10 and order_count(book, NOV) == 1
    assert book.extent.end == date(2026, 11, 1)
    assert any(ref.unit == "synthetic_returns" for ref in book.orders[0].refs)


def test_repeated_header_join_does_not_multiply_lines():
    headers = bind([r("A"), r("A")], role="headers", unit="synthetic_headers")
    lines = bind([r("A", "10", status="", day=""), r("A", "20", status="", day="")])
    book = adapt_sources([headers, lines])
    assert revenue_total(book, NOV) == 30 and order_count(book, NOV) == 1


def test_decimal_exactness_final_vnd_rounding_and_missing_money_independence():
    book = adapt_sources(
        [bind([r("A", "9007199254740993"), r("B", "0.5"), r("C", "0.5")])]
    )
    assert revenue_total(book, NOV) == Decimal("9007199254740994")
    broken = adapt_sources([bind([r("A", "not money")])])
    assert order_count(broken, NOV) == 1
    with pytest.raises(DomainAbstain):
        revenue_total(broken, NOV)
    only_headers = adapt_sources([bind([r("A")], role="headers")])
    assert order_count(only_headers, NOV) == 1
    with pytest.raises(DomainAbstain):
        revenue_total(only_headers, NOV)
    missing = r("A")
    del missing["net"]
    incomplete_money = adapt_sources([bind([missing])])
    assert order_count(incomplete_money, NOV) == 1
    with pytest.raises(DomainAbstain):
        revenue_total(incomplete_money, NOV)


def test_unknown_ambiguous_or_missing_filter_abstains_instead_of_ignoring():
    entities = {"product": EntityBinding("product", "name", "line")}
    book = adapt_sources(
        [
            bind(
                [
                    r("A", product="P", name="same"),
                    r("A", "50", product="Q", name="same"),
                    r("B", product="P", name="same"),
                ],
                entities=entities,
            )
        ]
    )
    assert revenue_total(book, NOV, [Filter("product", "P")]) == 200
    assert order_count(book, NOV, [Filter("product", "P")]) == 2
    for filters in [
        [Filter("product", "same")],
        [Filter("product", "unknown")],
        [Filter("channel", "P")],
    ]:
        with pytest.raises(DomainAbstain):
            revenue_total(book, NOV, filters)
    missing = adapt_sources(
        [
            bind(
                [r("A", product="P", name="Tea"), r("B", product="", name="")],
                entities=entities,
            )
        ]
    )
    with pytest.raises(DomainAbstain):
        order_count(missing, NOV, [Filter("product", "P")])


def test_order_filter_and_line_filter_both_apply():
    entities = {
        "product": EntityBinding("product", None, "line"),
        "customer": EntityBinding("customer", None, "order", blank_is_absent=True),
    }
    book = adapt_sources(
        [
            bind(
                [
                    r("A", product="P", customer="C"),
                    r("B", product="P", customer="D"),
                    r("C", product="Q", customer="C"),
                    r("D", product="P", customer=""),
                ],
                entities=entities,
            )
        ]
    )
    filters = [Filter("product", "P"), Filter("customer", "C")]
    assert (
        revenue_total(book, NOV, filters) == 100
        and order_count(book, NOV, filters) == 1
    )


def test_period_outside_data_is_not_zero_and_gap_inside_extent_is_zero():
    book = adapt_sources([bind([r("A", day="2026-11-01"), r("B", day="2026-11-03")])])
    gap = Period(date(2026, 11, 2), date(2026, 11, 2))
    assert revenue_total(book, gap) == 0 and order_count(book, gap) == 0
    with pytest.raises(DomainAbstain):
        order_count(book, Period(date(2026, 10, 1), date(2026, 10, 31)))
    assert order_count(book, Period(date(2026, 10, 1), date(2026, 11, 1))) == 1


def test_explicit_number_and_date_formats_are_not_guessed():
    book = adapt_sources(
        [
            bind(
                [r("A", "1.234,50", day="01/11/2026")],
                number_format="vi",
                date_format="%d/%m/%Y",
            )
        ]
    )
    assert revenue_total(book, NOV) == 1235
    other = adapt_sources([bind([r("A", "1,234")])])
    with pytest.raises(DomainAbstain):
        revenue_total(other, NOV)


@pytest.mark.parametrize("status", ["return", "cancel"])
def test_header_cannot_hide_conflicting_nonempty_line_status(status):
    headers = bind([r("A")], role="headers", unit="synthetic_headers")
    lines = bind([r("A", status=status)])
    with pytest.raises(DomainAbstain):
        adapt_sources([headers, lines])


def test_header_cannot_hide_conflicting_nonempty_order_entity():
    entities = {"customer": EntityBinding("customer", None, "order")}
    headers = bind(
        [r("A", customer="C")],
        role="headers",
        unit="synthetic_headers",
        entities=entities,
    )
    lines = bind([r("A", customer="D")], entities=entities)
    with pytest.raises(DomainAbstain):
        adapt_sources([headers, lines])
