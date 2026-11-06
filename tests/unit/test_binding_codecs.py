from datetime import date
from decimal import Decimal

import pytest

from datamate.domain_lib.orders import Binding, BoundSource, RawRow, adapt_sources


@pytest.mark.parametrize("money", ["560,000", "560000", "1,234.50"])
def test_explicit_en_money_codec(money):
    binding = Binding(
        "lines",
        "id",
        "day",
        "status",
        "net",
        {"ok": "completed"},
        number_format="en",
        date_format="%d thg %m %Y",
    )
    book = adapt_sources(
        [
            BoundSource(
                "synthetic",
                "0" * 64,
                binding,
                [RawRow(1, dict(id="A", day="1 thg 6 2025", status="ok", net=money))],
            )
        ]
    )
    assert book.orders[0].placed_at == date(2025, 6, 1)
    assert book.orders[0].lines[0].amount == Decimal(money.replace(",", ""))


def test_bad_grouping_remains_unknown_money():
    binding = Binding(
        "lines", "id", "day", "status", "net", {"ok": "completed"}, number_format="en"
    )
    book = adapt_sources(
        [
            BoundSource(
                "synthetic",
                "0" * 64,
                binding,
                [RawRow(1, dict(id="A", day="2026-11-07", status="ok", net="12,34"))],
            )
        ]
    )
    assert book.orders[0].lines[0].amount is None
