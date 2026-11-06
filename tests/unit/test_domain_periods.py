from datetime import date

import pytest

from datamate.domain_lib.model import DomainAbstain, Period
from datamate.domain_lib.periods import previous_period, resolve_period


@pytest.mark.parametrize(
    "text,anchor,start,end",
    [
        ("hôm nay", "2026-11-07", "2026-11-07", "2026-11-07"),
        ("hom qua", "2026-01-01", "2025-12-31", "2025-12-31"),
        ("7 ngày gần đây", "2026-01-03", "2025-12-28", "2026-01-03"),
        ("tuần này", "2026-11-02", "2026-11-02", "2026-11-02"),
        ("tuần trước", "2026-11-02", "2026-10-26", "2026-11-01"),
        ("tháng này", "2024-03-31", "2024-03-01", "2024-03-31"),
        ("tháng trước", "2024-03-02", "2024-02-01", "2024-02-29"),
        ("tháng 2/2024", "2026-11-07", "2024-02-01", "2024-02-29"),
        ("tháng 12", "2026-11-07", "2025-12-01", "2025-12-31"),
        ("quý 4 năm 2024", "2026-11-07", "2024-10-01", "2024-12-31"),
        ("quý 4", "2026-03-01", "2025-10-01", "2025-12-31"),
        ("năm 2025", "2026-11-07", "2025-01-01", "2025-12-31"),
        ("từ đầu năm đến nay", "2026-11-07", "2026-01-01", "2026-11-07"),
        ("2024-02-29", "2026-11-07", "2024-02-29", "2024-02-29"),
        ("ngày 29/2/2024", "2026-11-07", "2024-02-29", "2024-02-29"),
        ("từ 01/02/2024 đến 29/02/2024", "2026-11-07", "2024-02-01", "2024-02-29"),
    ],
)
def test_period_boundaries(text, anchor, start, end):
    assert resolve_period(text, date.fromisoformat(anchor)) == Period(
        date.fromisoformat(start), date.fromisoformat(end)
    )


@pytest.mark.parametrize(
    "text",
    [
        "tháng 13/2025",
        "ngày 29/2/2025",
        "từ 2/1/2026 đến 1/1/2026",
        "tháng 1 và tháng 2",
        "Tết 2026",
        "hôm nay của khách A",
        "0 ngày gần đây",
        "9999999 ngày gần đây",
        "",
        "2026-02-30",
    ],
)
def test_unknown_ambiguous_invalid_period_abstains(text):
    with pytest.raises(DomainAbstain):
        resolve_period(text, date(2026, 11, 7))


def test_comparison_month_to_date_is_not_full_previous_month():
    assert previous_period("tháng này", date(2026, 3, 12)) == Period(
        date(2026, 2, 1), date(2026, 2, 12)
    )
    assert previous_period("tháng này", date(2024, 3, 31)) == Period(
        date(2024, 2, 1), date(2024, 2, 29)
    )
    assert previous_period("tháng 3/2024", date(2024, 3, 12)) == Period(
        date(2024, 2, 1), date(2024, 2, 29)
    )
    assert previous_period("tuần này", date(2026, 11, 3)) == Period(
        date(2026, 10, 26), date(2026, 11, 1)
    )
    with pytest.raises(DomainAbstain):
        previous_period("từ 1/1/2026 đến 3/1/2026", date(2026, 11, 7))


def test_relative_current_period_cannot_include_future_records():
    assert resolve_period("tháng 11", date(2026, 11, 7)) == Period(
        date(2026, 11, 1), date(2026, 11, 7)
    )
    assert resolve_period("quý 4", date(2026, 11, 7)) == Period(
        date(2026, 10, 1), date(2026, 11, 7)
    )
    assert previous_period("quý 1 năm 2026", date(2026, 11, 7)) == Period(
        date(2025, 10, 1), date(2025, 12, 31)
    )
    with pytest.raises(DomainAbstain):
        previous_period("quý 4", date(2026, 11, 7))
