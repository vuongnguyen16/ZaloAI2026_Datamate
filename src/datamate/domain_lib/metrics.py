"""Exact CPU aggregation over a verified ledger; no query/model execution."""

from decimal import ROUND_HALF_UP, Decimal, localcontext

from .model import DomainAbstain, Period
from .orders import Filter, Ledger, alias


def _filters(ledger, filters):
    resolved = []
    seen = set()
    if len(filters) > 16:
        raise DomainAbstain("filter_resource_limit")
    for item in filters:
        if (
            not isinstance(item, Filter)
            or item.dimension in seen
            or not isinstance(item.mention, str)
            or not 0 < len(item.mention) <= 512
        ):
            raise DomainAbstain("invalid_filter")
        seen.add(item.dimension)
        catalog = ledger.catalogs.get(item.dimension)
        if catalog is None:
            raise DomainAbstain("unsupported_filter")
        matches = (
            {item.mention}
            if item.mention in catalog.codes
            else catalog.aliases.get(alias(item.mention), frozenset())
        )
        if len(matches) != 1:
            raise DomainAbstain("unknown_or_ambiguous_entity")
        resolved.append((item.dimension, next(iter(matches)), catalog.scope))
    return resolved


def _matches(entities, filters):
    results = []
    for dim, code, _ in filters:
        value = entities.get(dim)
        if value is None or (value.code is None and not value.absent):
            results.append(None)
        else:
            results.append(not value.absent and value.code == code)
    if False in results:
        return False
    if None in results:
        raise DomainAbstain("missing_filter_entity")
    return True


def _selected(ledger, period, filters):
    if not isinstance(ledger, Ledger) or not isinstance(period, Period):
        raise DomainAbstain("invalid_metric_input")
    resolved = _filters(ledger, filters)
    if period.end < ledger.extent.start or period.start > ledger.extent.end:
        raise DomainAbstain("period_outside_data")
    order_filters = [f for f in resolved if f[2] == "order"]
    line_filters = [f for f in resolved if f[2] == "line"]
    for order in ledger.orders:
        if (
            order.status not in {"completed", "shipping"}
            or not period.start <= order.placed_at <= period.end
        ):
            continue
        if not _matches(order.entities, order_filters):
            continue
        if line_filters and not order.lines:
            raise DomainAbstain("missing_order_details")
        selected = []
        uncertain = False
        for line in order.lines:
            try:
                if _matches(line.entities, line_filters):
                    selected.append(line)
            except DomainAbstain:
                uncertain = True
        if uncertain:
            raise DomainAbstain("missing_filter_entity")
        if not line_filters or selected:
            yield order, selected


def order_count(ledger: Ledger, period: Period, filters=()) -> int:
    return sum(1 for _ in _selected(ledger, period, filters))


def revenue_total(ledger: Ledger, period: Period, filters=()) -> Decimal:
    with localcontext() as context:
        context.prec = 128
        total = Decimal(0)
        for order, lines in _selected(ledger, period, filters):
            if not order.lines or any(line.amount is None for line in lines):
                raise DomainAbstain("missing_or_invalid_line_amount")
            total += sum((line.amount for line in lines), Decimal(0))
        return total.quantize(Decimal(1), rounding=ROUND_HALF_UP)
