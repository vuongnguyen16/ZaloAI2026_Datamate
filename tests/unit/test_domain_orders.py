from copy import deepcopy
from datetime import date

import pytest

from datamate.domain_lib.model import DomainAbstain
from datamate.domain_lib.orders import (
    Binding,
    BoundSource,
    EntityBinding,
    RawRow,
    adapt_sources,
)

STATUS = {
    "done": "completed",
    "ship": "shipping",
    "cancel": "cancelled",
    "return": "returned",
}


def source(rows, *, role="lines", unit="synthetic", **kwargs):
    binding = Binding(
        role=role,
        order_id="id",
        placed_at="day",
        status="status",
        amount="net" if role == "lines" else None,
        status_values=STATUS,
        **kwargs,
    )
    return BoundSource(
        unit, "0" * 64, binding, [RawRow(i + 1, row) for i, row in enumerate(rows)]
    )


def row(qid="A", day="2026-11-01", status="done", net="10", **extra):
    return dict(id=qid, day=day, status=status, net=net, **extra)


def test_exact_same_order_duplicates_keep_lineage_but_different_ids_do_not():
    raw = [row(), row(), row("B")]
    before = deepcopy(raw)
    book = adapt_sources([source(raw)])
    assert raw == before and len(book.orders) == 2
    assert len(book.orders[0].lines) == 1 and len(book.orders[0].lines[0].refs) == 2
    assert book.extent.start == date(2026, 11, 1)
    assert book.provenance[0][1] == "0" * 64


def test_carry_is_scoped_to_order_group_and_not_amount():
    book = adapt_sources(
        [source([row(), row("", day="", status="", net="20")], carry_order_fields=True)]
    )
    assert len(book.orders) == 1 and len(book.orders[0].lines) == 2
    with pytest.raises(DomainAbstain):
        adapt_sources(
            [source([row(), row("B", day="", status="")], carry_order_fields=True)]
        )
    with pytest.raises(DomainAbstain):
        adapt_sources([source([row(), row("", day="", status="")])])


@pytest.mark.parametrize(
    "rows",
    [
        [row(status="unknown")],
        [row(day="01/11/2026")],
        [row(), row(day="2026-11-02")],
        [row(), row(status="ship")],
        [row(qid="")],
    ],
)
def test_unknown_or_conflicting_grain_metadata_abstains(rows):
    with pytest.raises(DomainAbstain):
        adapt_sources([source(rows)])


def test_resource_limits_and_unknown_source_roles_never_silently_drop_rows():
    with pytest.raises(DomainAbstain):
        adapt_sources([source([row(), row("B")])], max_rows=1)
    with pytest.raises(DomainAbstain):
        adapt_sources([source([row()], role="receipts")])
    with pytest.raises(DomainAbstain):
        adapt_sources([source([row()])], max_bytes=1)


def test_entity_binding_records_order_and_line_scope_explicitly():
    entities = {
        "product": EntityBinding("product", "product_name", "line"),
        "customer": EntityBinding("customer", None, "order"),
    }
    book = adapt_sources(
        [
            source(
                [
                    row(product="P", product_name="Tea", customer="C"),
                    row(
                        "",
                        day="",
                        status="",
                        net="20",
                        product="Q",
                        product_name="Coffee",
                        customer="",
                    ),
                ],
                entities=entities,
                carry_order_fields=True,
            )
        ]
    )
    assert book.orders[0].entities["customer"].code == "C"
    assert [line.entities["product"].code for line in book.orders[0].lines] == [
        "P",
        "Q",
    ]
