"""Conservative header/README rules and data diagnostics. No IDs or gold rules."""

import hashlib
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from decimal import localcontext

from .model import DomainAbstain
from .orders import Binding, _date, _money

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d thg %m %Y")
NUMBER_FORMATS = ("plain", "en", "vi")


def norm(text):
    value = unicodedata.normalize("NFD", str(text).casefold().replace("đ", "d"))
    return re.sub(
        r"[^a-z0-9]", "", "".join(c for c in value if unicodedata.category(c) != "Mn")
    )


STATUS = {
    norm(k): v
    for v, names in {
        "completed": ["Hoàn thành", "Đã hoàn thành", "Hoàn tất", "Đã xong", "Xong"],
        "shipping": ["Đang giao", "Đang giao hàng", "Đang vận chuyển"],
        "cancelled": ["Huỷ", "Đã hủy", "Hủy đơn", "Đã huỷ đơn", "Đã hủy hàng"],
        "returned": [
            "Trả hàng",
            "Đã trả hàng",
            "Hoàn trả",
            "Trả lại",
            "Đổi trả",
            "Đã hoàn hàng",
        ],
    }.items()
    for k in names
}

ROLES = {
    "id": {"madon", "madonhang", "mahoadon", "orderid"},
    "day": {
        "ngayban",
        "ngaydat",
        "ngaydathang",
        "ngaydon",
        "ngaylap",
        "thoigian",
        "orderdate",
    },
    "status": {"trangthaidon", "trangthaidonhang", "trangthai", "orderstatus"},
    "qty": {"soluong", "soluongsanpham", "quantity", "qty", "sl"},
    "price": {"dongia", "giasanpham", "unitprice"},
    "product": {"tenhang", "tensanpham", "sanpham", "product"},
    "discount": {"giamgiadong", "giamgiatrenmo idong", "linediscount"},
}


def definitions(readme):
    current = None
    result = {}
    for line in readme.splitlines():
        match = re.fullmatch(r"#{2,3}\s+Cột trong `([^`]+)`\s*", line)
        if match:
            current = match[1].casefold()
            result.setdefault(current, {})
            continue
        if line.startswith("#"):
            current = None
        match = re.fullmatch(r"\s*-\s+\*\*(.+?)\*\*:\s*(.+)", line)
        if current is not None and match:
            key = norm(match[1])
            value = match[2].strip()
            if key in result[current] and result[current][key] != value:
                raise DomainAbstain("conflicting_readme_definition")
            result[current][key] = value
    return result


def header(column):
    if column.get("declared_name"):
        return column["declared_name"]
    cells = []
    for record in column.get("header_cells", []):
        value = record.get("cell")
        if isinstance(value, dict):
            value = value.get("value") if value.get("truncated") is not True else None
        if isinstance(value, str) and value.strip():
            cells.append(value)
    return cells[-1] if cells else ""


@dataclass(frozen=True)
class Candidate:
    unit: dict
    role: str
    columns: dict
    net_semantics: bool
    evidence: dict
    reasons: tuple[str, ...] = ()


def propose(unit, readme):
    dictionary = definitions(readme).get(unit["source_file"].casefold(), {})
    found = {role: [] for role in ROLES}
    found["amount"] = []
    evidence = {}
    net = set()
    for column in unit["columns"]:
        label = header(column)
        description = dictionary.get(norm(label), "")
        name = column["sql_name"]
        for role, terms in ROLES.items():
            if norm(description) in terms or norm(label) in terms:
                found[role].append(name)
                evidence[name] = dict(label=label, definition=description)
        description_key = norm(description)
        if description_key.startswith("thanhtiensaugiam") or description_key in {
            "thanhtiendongdasaugiamgia",
            "thanhtiendasaugiamgiadong",
        }:
            net.add(name)
            found["amount"].append(name)
            evidence[name] = dict(label=label, definition=description)
        elif description_key.startswith("thanhtien") or norm(label) in {
            "thanhtien",
            "tongtien",
            "netline",
            "net",
        }:
            found["amount"].append(name)
            evidence[name] = dict(label=label, definition=description)
    columns = {role: values[0] for role, values in found.items() if len(values) == 1}
    reasons = []
    if (
        unit.get("header_status") not in {"auto_rule", "explicit", "schema"}
        or unit.get("data_start_row") is None
    ):
        reasons.append("unresolved_header")
    if any(len(found[r]) != 1 for r in ("id", "day", "status")):
        reasons.append("missing_or_ambiguous_order_columns")
    role = (
        "lines"
        if "product" in columns and ("qty" in columns or "amount" in columns)
        else "headers"
    )
    return Candidate(
        unit, role, columns, columns.get("amount") in net, evidence, tuple(reasons)
    )


def classify_row(row, candidate):
    if row.row < (candidate.unit.get("data_start_row") or 1):
        return "prefix"
    values = row.cells
    if not any(v is not None and v.strip() for v in values.values()):
        return "blank"
    labels = {c["sql_name"]: header(c) for c in candidate.unit["columns"]}
    if all((values.get(c) or "").strip() == label for c, label in labels.items()):
        return "repeated_header"
    col = candidate.columns
    qid = (values.get(col.get("id")) or "").strip()
    marker = qid or (next(iter(values.values())) or "").strip()
    if norm(marker) in {"tong", "tongcong", "total", "grandtotal"} and not any(
        (values.get(col.get(k)) or "").strip() for k in ("day", "status", "product")
    ):
        return "printed_total"
    return "data"


def inspect_rows(rows, candidate):
    col = candidate.columns
    date_fail = Counter()
    date_n = 0
    status = Counter()
    missing_net = 0
    numbers = {
        fmt: dict(parsed=0, total=0, matched=0, digest=hashlib.sha256())
        for fmt in NUMBER_FORMATS
    }
    date_bindings = {
        fmt: Binding(
            candidate.role,
            col.get("id", "id"),
            col.get("day"),
            col.get("status"),
            date_format=fmt,
        )
        for fmt in DATE_FORMATS
    }
    number_bindings = {
        fmt: Binding(
            candidate.role,
            col.get("id", "id"),
            col.get("day"),
            col.get("status"),
            number_format=fmt,
        )
        for fmt in NUMBER_FORMATS
    }
    count = 0
    for row in rows:
        count += 1
        values = row.cells
        value = (values.get(col.get("day")) or "").strip()
        if value:
            date_n += 1
            for fmt, binding in date_bindings.items():
                try:
                    _date(value, binding)
                except DomainAbstain:
                    date_fail[fmt] += 1
        value = (values.get(col.get("status")) or "").strip()
        if value:
            status[value] += 1
        amount = (values.get(col.get("amount")) or "").strip() or None
        if amount is None:
            missing_net += 1
        for fmt, binding in number_bindings.items():
            parsed = _money(amount, binding)
            if parsed is not None:
                numbers[fmt]["parsed"] += 1
                with localcontext() as ctx:
                    ctx.prec = 128
                    numbers[fmt]["digest"].update(
                        str(parsed.normalize()).encode() + b"\0"
                    )
            if "qty" in col and "price" in col:
                numbers[fmt]["total"] += 1
                qty = _money((values.get(col["qty"]) or "").strip(), binding)
                price = _money((values.get(col["price"]) or "").strip(), binding)
                discount = (
                    _money((values.get(col["discount"]) or "").strip(), binding)
                    if "discount" in col
                    else 0
                )
                if None not in (qty, price, parsed, discount):
                    with localcontext() as ctx:
                        ctx.prec = 128
                        numbers[fmt]["matched"] += parsed == qty * price - discount
    reasons = list(candidate.reasons)
    dates = [fmt for fmt in DATE_FORMATS if date_fail[fmt] == 0 and date_n]
    date_format = dates[0] if len(dates) == 1 else None
    if date_format is None:
        reasons.append("date_format_unverified")
    unknown = sum(n for label, n in status.items() if norm(label) not in STATUS)
    if unknown:
        reasons.append("unknown_status")
    if not status:
        reasons.append("missing_status_inventory")
    if not candidate.net_semantics:
        reasons.append("net_semantics_missing")
    valid = [fmt for fmt in NUMBER_FORMATS if numbers[fmt]["parsed"] == count and count]
    fingerprints = {numbers[fmt]["digest"].hexdigest() for fmt in valid}
    chosen = None
    if len(fingerprints) == 1:
        chosen = max(valid, key=lambda f: numbers[f]["matched"])
    elif len(fingerprints) > 1:
        fitting = [
            fmt
            for fmt in valid
            if numbers[fmt]["total"] >= 10
            and numbers[fmt]["matched"] / numbers[fmt]["total"] >= 0.95
        ]
        if (
            len({numbers[fmt]["digest"].hexdigest() for fmt in fitting}) == 1
            and fitting
        ):
            chosen = fitting[0]
        else:
            reasons.append("number_scale_ambiguous")
    if chosen is None:
        reasons.append("amount_format_unverified")
    if (
        chosen
        and numbers[chosen]["total"]
        and numbers[chosen]["matched"] / numbers[chosen]["total"] < 0.95
    ):
        reasons.append("arithmetic_screen_failed")
    if missing_net:
        reasons.append("missing_net_amount")
    count_ok = (
        not candidate.reasons
        and date_format is not None
        and not unknown
        and bool(status)
    )
    revenue_ok = (
        count_ok
        and candidate.role == "lines"
        and candidate.net_semantics
        and chosen is not None
        and not missing_net
        and "arithmetic_screen_failed" not in reasons
    )
    return dict(
        rows=count,
        date_format=date_format,
        number_format=chosen,
        count_format_ok=count_ok,
        revenue_format_ok=revenue_ok,
        unknown_status_rows=unknown,
        status_counts=dict(status),
        status_values={s: STATUS[norm(s)] for s in status if norm(s) in STATUS},
        arithmetic={
            fmt: {k: v for k, v in data.items() if k != "digest"}
            for fmt, data in numbers.items()
        },
        reasons=sorted(set(reasons)),
    )
