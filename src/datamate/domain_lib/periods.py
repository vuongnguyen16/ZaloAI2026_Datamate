"""Strict period fragments; no fuzzy substring search or external calendar guesses."""

import calendar
import re
import unicodedata
from datetime import date, timedelta

from .model import DomainAbstain, Period


def _text(value):
    if not isinstance(value, str) or not 0 < len(value) <= 256:
        raise DomainAbstain("unsupported_period")
    value = unicodedata.normalize("NFD", value.lower().replace("đ", "d"))
    return " ".join(
        "".join(c for c in value if unicodedata.category(c) != "Mn").split()
    )


def _month(year, month):
    return Period(
        date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    )


def _shift_month(year, month, delta):
    total = year * 12 + month - 1 + delta
    return divmod(total, 12)[0], divmod(total, 12)[1] + 1


def _day(fragment):
    fragment = fragment.removeprefix("ngay ")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", fragment):
        return date.fromisoformat(fragment)
    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", fragment)
    if match:
        day, month, year = map(int, match.groups())
        return date(year, month, day)
    raise DomainAbstain("unsupported_period")


def _parse(text, anchor):
    if type(anchor) is not date:
        raise DomainAbstain("invalid_anchor")
    text = _text(text)
    text = text.removeprefix("trong ")
    if text in ("hom nay", "hom qua"):
        day = anchor - timedelta(days=text == "hom qua")
        return Period(day, day), "day"
    match = re.fullmatch(r"(\d{1,4}) ngay (?:gan day|gan nhat)", text)
    if match:
        n = int(match[1])
        if not 1 <= n <= 3660:
            raise DomainAbstain("period_resource_limit")
        return Period(anchor - timedelta(days=n - 1), anchor), "rolling"
    if text in ("tuan nay", "tuan truoc", "tuan roi"):
        monday = anchor - timedelta(days=anchor.weekday())
        if text == "tuan nay":
            return Period(monday, anchor), "week"
        return Period(monday - timedelta(days=7), monday - timedelta(days=1)), "week"
    if text in ("thang nay", "thang truoc", "thang roi"):
        if text == "thang nay":
            return Period(anchor.replace(day=1), anchor), "month_to_date"
        return _month(*_shift_month(anchor.year, anchor.month, -1)), "month"
    if text in ("nam nay", "tu dau nam", "tu dau nam den nay", "tu dau nam toi nay"):
        return Period(date(anchor.year, 1, 1), anchor), "year_to_date"
    match = re.fullmatch(r"tu (.+) (?:den|toi) (.+)", text)
    if match:
        return Period(_day(match[1]), _day(match[2])), "range"
    match = re.fullmatch(r"(?:thang )?(\d{1,2})(?:/| nam )(\d{4})", text)
    if match:
        return _month(int(match[2]), int(match[1])), "month"
    match = re.fullmatch(r"thang (\d{1,2})", text)
    if match:
        month = int(match[1])
        year = anchor.year - (month > anchor.month)
        period = _month(year, month)
        return Period(period.start, min(period.end, anchor)), "month"
    match = re.fullmatch(r"quy ([1-4])(?: nam (\d{4}))?", text)
    if match:
        quarter = int(match[1])
        month = (quarter - 1) * 3 + 1
        year = int(match[2]) if match[2] else anchor.year - (month > anchor.month)
        period = Period(date(year, month, 1), _month(year, month + 2).end)
        return (
            period if match[2] else Period(period.start, min(period.end, anchor))
        ), "quarter"
    match = re.fullmatch(r"nam (\d{4})", text)
    if match:
        year = int(match[1])
        return Period(date(year, 1, 1), date(year, 12, 31)), "year"
    day = _day(text)
    return Period(day, day), "day"


def resolve_period(text: str, as_of: date) -> Period:
    try:
        return _parse(text, as_of)[0]
    except (ValueError, OverflowError, TypeError) as exc:
        if isinstance(exc, DomainAbstain):
            raise
        raise DomainAbstain("invalid_period") from None


def previous_period(text: str, as_of: date) -> Period:
    try:
        period, kind = _parse(text, as_of)
        if kind in ("month", "month_to_date"):
            prior = _month(*_shift_month(period.start.year, period.start.month, -1))
            if kind == "month_to_date":
                return Period(
                    prior.start, prior.end.replace(day=min(as_of.day, prior.end.day))
                )
            return prior
        if kind == "day":
            day = period.start - timedelta(days=1)
            return Period(day, day)
        if kind == "week":
            return Period(
                period.start - timedelta(days=7), period.start - timedelta(days=1)
            )
        if (
            kind == "quarter"
            and period.end == _month(period.start.year, period.start.month + 2).end
        ):
            year, month = _shift_month(period.start.year, period.start.month, -3)
            return Period(date(year, month, 1), _month(year, month + 2).end)
        if kind == "year":
            return Period(
                date(period.start.year - 1, 1, 1), date(period.start.year - 1, 12, 31)
            )
        raise DomainAbstain("unsupported_comparison")
    except (ValueError, OverflowError, TypeError) as exc:
        if isinstance(exc, DomainAbstain):
            raise
        raise DomainAbstain("invalid_period") from None
