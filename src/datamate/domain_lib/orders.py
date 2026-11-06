"""Build a conservative ledger from explicitly bound raw rows, without SQL joins."""

import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from types import MappingProxyType
from typing import Iterable, Mapping

from .model import DomainAbstain, Period

STATUSES = frozenset({"completed", "shipping", "cancelled", "returned"})


def alias(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


@dataclass(frozen=True)
class EntityBinding:
    code: str | None
    label: str | None = None
    scope: str = "line"
    blank_is_absent: bool = False

    def __post_init__(self):
        if self.scope not in {"line", "order"} or not (self.code or self.label):
            raise DomainAbstain("invalid_entity_binding")


@dataclass(frozen=True)
class Binding:
    role: str
    order_id: str
    placed_at: str | None
    status: str | None
    amount: str | None = None
    status_values: Mapping[str, str] = field(default_factory=dict)
    entities: Mapping[str, EntityBinding] = field(default_factory=dict)
    carry_order_fields: bool = False
    date_format: str = "%Y-%m-%d"
    number_format: str = "plain"

    def __post_init__(self):
        if (
            self.role not in {"lines", "headers", "events"}
            or not self.order_id
            or self.date_format not in {"%Y-%m-%d", "%d/%m/%Y"}
            or self.number_format not in {"plain", "vi"}
        ):
            raise DomainAbstain("unsupported_binding")
        if self.role == "events" and not self.status:
            raise DomainAbstain("event_status_required")
        if not all(
            isinstance(k, str) and k and v in STATUSES
            for k, v in self.status_values.items()
        ):
            raise DomainAbstain("invalid_status_mapping")
        if len(self.entities) > 16 or not all(
            isinstance(k, str) and 0 < len(k) <= 64 and isinstance(v, EntityBinding)
            for k, v in self.entities.items()
        ):
            raise DomainAbstain("invalid_entity_mapping")
        object.__setattr__(
            self, "status_values", MappingProxyType(dict(self.status_values))
        )
        object.__setattr__(self, "entities", MappingProxyType(dict(self.entities)))

    def fingerprint(self):
        value = {
            k: getattr(self, k)
            for k in (
                "role",
                "order_id",
                "placed_at",
                "status",
                "amount",
                "carry_order_fields",
                "date_format",
                "number_format",
            )
        }
        value.update(
            status_values=dict(self.status_values),
            entities={k: asdict(v) for k, v in self.entities.items()},
        )
        return hashlib.sha256(
            json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()


@dataclass(frozen=True)
class RawRow:
    row: int
    cells: Mapping[str, str | None]


@dataclass(frozen=True)
class BoundSource:
    unit: str
    sha256: str
    binding: Binding
    rows: Iterable[RawRow]


@dataclass(frozen=True)
class SourceRef:
    unit: str
    row: int


@dataclass(frozen=True)
class Entity:
    code: str | None
    label: str | None
    absent: bool = False


@dataclass(frozen=True)
class Line:
    amount: Decimal | None
    entities: Mapping[str, Entity]
    refs: tuple[SourceRef, ...]


@dataclass(frozen=True)
class Order:
    key: str
    placed_at: date
    status: str
    entities: Mapping[str, Entity]
    lines: tuple[Line, ...]
    refs: tuple[SourceRef, ...]


@dataclass(frozen=True)
class Catalog:
    scope: str
    codes: frozenset[str]
    aliases: Mapping[str, frozenset[str]]


@dataclass(frozen=True)
class Ledger:
    orders: tuple[Order, ...]
    extent: Period
    catalogs: Mapping[str, Catalog]
    provenance: tuple[tuple[str, str, str], ...]


@dataclass(frozen=True)
class Filter:
    dimension: str
    mention: str


def _cell(cells, column):
    if column is None:
        return None
    value = cells.get(column)
    return value.strip() if value is not None and value.strip() else None


def _date(value, binding):
    if value is None:
        return None
    try:
        return (
            date.fromisoformat(value)
            if binding.date_format == "%Y-%m-%d"
            else datetime.strptime(value, binding.date_format).date()
        )
    except (ValueError, TypeError):
        raise DomainAbstain("invalid_order_date") from None


def _money(value, binding):
    if value is None or len(value) > 128:
        return None
    if binding.number_format == "vi":
        if not re.fullmatch(r"[+-]?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?", value):
            return None
        value = value.replace(".", "").replace(",", ".")
    elif not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value):
        return None
    result = Decimal(value)
    return (
        result
        if len(result.as_tuple().digits) <= 64 and result.as_tuple().exponent >= -12
        else None
    )


def _one(values, code):
    values = {v for v in values if v is not None}
    if len(values) != 1:
        raise DomainAbstain(code)
    return next(iter(values))


def _entity(values):
    codes = {v.code for v in values if v.code is not None}
    if len(codes) > 1 or (codes and any(v.absent for v in values)):
        raise DomainAbstain("conflicting_order_entity")
    if not values or any(v.code is None and not v.absent for v in values):
        return Entity(None, None)
    return values[0]


def adapt_sources(
    sources: Iterable[BoundSource], *, max_rows=100000, max_bytes=32 * 1024**2
) -> Ledger:
    """Bindings must be verified by the caller. Hashes record identity, not truth."""
    if (
        type(max_rows) is not int
        or type(max_bytes) is not int
        or max_rows < 1
        or max_bytes < 1
    ):
        raise DomainAbstain("invalid_resource_limit")
    groups = defaultdict(list)
    events = defaultdict(set)
    event_refs = defaultdict(list)
    dimensions = {}
    aliases = defaultdict(lambda: defaultdict(set))
    codes = defaultdict(set)
    provenance = []
    units = set()
    count = retained = 0
    for source in sources:
        if (
            not isinstance(source, BoundSource)
            or not isinstance(source.unit, str)
            or not 0 < len(source.unit) <= 512
            or source.unit in units
            or not re.fullmatch(r"[0-9a-f]{64}", source.sha256)
        ):
            raise DomainAbstain("invalid_source_provenance")
        units.add(source.unit)
        if len(units) > 1024:
            raise DomainAbstain("source_resource_limit")
        b = source.binding
        provenance.append((source.unit, source.sha256, b.fingerprint()))
        for dim, definition in b.entities.items():
            if dim in dimensions and dimensions[dim] != definition.scope:
                raise DomainAbstain("conflicting_entity_scope")
            dimensions[dim] = definition.scope
        last_id = None
        carry = {}
        previous_row = 0
        for raw in source.rows:
            count += 1
            if (
                count > max_rows
                or not isinstance(raw, RawRow)
                or type(raw.row) is not int
                or raw.row <= previous_row
                or len(raw.cells) > 1024
            ):
                raise DomainAbstain("row_resource_or_coordinate")
            previous_row = raw.row
            cells = dict(raw.cells)
            if not all(
                isinstance(k, str) and k and (v is None or isinstance(v, str))
                for k, v in cells.items()
            ):
                raise DomainAbstain("raw_string_cells_required")
            retained += sum(
                64 + len(k.encode("utf-8")) + len((v or "").encode("utf-8"))
                for k, v in cells.items()
            )
            if retained > max_bytes:
                raise DomainAbstain("row_byte_limit")
            signature = hashlib.sha256(
                json.dumps(sorted(cells.items()), ensure_ascii=False).encode()
            ).hexdigest()
            qid = _cell(cells, b.order_id)
            if qid is None:
                if not b.carry_order_fields or last_id is None:
                    raise DomainAbstain("missing_order_id")
                qid = last_id
            if len(qid) > 512:
                raise DomainAbstain("order_id_limit")
            if qid != last_id:
                carry = {}
            fields = [b.placed_at, b.status] + [
                col
                for d in b.entities.values()
                if d.scope == "order"
                for col in (d.code, d.label)
            ]
            values = {
                column: _cell(cells, column) for column in fields if column is not None
            }
            if b.carry_order_fields:
                for column, value in values.items():
                    if value is not None:
                        carry[column] = value
                values = {
                    column: value if value is not None else carry.get(column)
                    for column, value in values.items()
                }
            last_id = qid
            when = _date(values.get(b.placed_at), b)
            raw_status = values.get(b.status)
            status = b.status_values.get(raw_status) if raw_status else None
            if raw_status and status is None:
                raise DomainAbstain("unknown_order_status")
            ref = SourceRef(source.unit, raw.row)
            if b.role == "events":
                if status not in {"cancelled", "returned"}:
                    raise DomainAbstain("unsupported_order_event")
                events[qid].add(status)
                event_refs[qid].append(ref)
                continue
            entities = {}
            for dim, definition in b.entities.items():
                fetch = (
                    (lambda col: values.get(col))
                    if definition.scope == "order"
                    else (lambda col: _cell(cells, col))
                )
                code = fetch(definition.code)
                label = fetch(definition.label)
                if definition.code is None and label:
                    code = alias(label)
                entity = Entity(
                    code,
                    label,
                    definition.blank_is_absent and code is None and label is None,
                )
                entities[dim] = entity
                if code:
                    codes[dim].add(code)
                    for text in (code, label):
                        if text:
                            aliases[dim][alias(text)].add(code)
            groups[qid].append(
                dict(
                    role=b.role,
                    date=when,
                    status=status,
                    entities=entities,
                    amount=_money(_cell(cells, b.amount), b)
                    if b.role == "lines"
                    else None,
                    signature=signature,
                    ref=ref,
                )
            )
    if not groups or set(events) - set(groups):
        raise DomainAbstain("missing_orders_or_orphan_events")
    orders = []
    for qid, records in sorted(groups.items()):
        headers = [r for r in records if r["role"] == "headers"]
        primary = headers or records
        placed = _one([r["date"] for r in primary], "ambiguous_order_date")
        status = _one([r["status"] for r in primary], "ambiguous_order_status")
        if (
            not headers
            and any(r["date"] is None or r["status"] is None for r in records)
        ) or any(r["date"] is not None and r["date"] != placed for r in records):
            raise DomainAbstain("conflicting_or_missing_order_date")
        if events[qid]:
            status = "returned" if "returned" in events[qid] else "cancelled"
        order_entities = {}
        for dim, scope in dimensions.items():
            if scope == "order":
                selected = [
                    r["entities"][dim] for r in headers if dim in r["entities"]
                ] or [r["entities"][dim] for r in records if dim in r["entities"]]
                order_entities[dim] = _entity(selected)
        lines = {}
        for record in records:
            if record["role"] != "lines":
                continue
            signature = record["signature"]
            if signature in lines:
                lines[signature][1].append(record["ref"])
            else:
                lines[signature] = (record, [record["ref"]])
        canonical = tuple(
            Line(
                r["amount"],
                MappingProxyType(
                    {
                        dim: v
                        for dim, v in r["entities"].items()
                        if dimensions[dim] == "line"
                    }
                ),
                tuple(refs),
            )
            for r, refs in lines.values()
        )
        orders.append(
            Order(
                qid,
                placed,
                status,
                MappingProxyType(order_entities),
                canonical,
                tuple(r["ref"] for r in records) + tuple(event_refs[qid]),
            )
        )
    catalogs = {
        dim: Catalog(
            scope,
            frozenset(codes[dim]),
            MappingProxyType({a: frozenset(v) for a, v in aliases[dim].items()}),
        )
        for dim, scope in dimensions.items()
    }
    extent = Period(min(o.placed_at for o in orders), max(o.placed_at for o in orders))
    return Ledger(tuple(orders), extent, MappingProxyType(catalogs), tuple(provenance))
