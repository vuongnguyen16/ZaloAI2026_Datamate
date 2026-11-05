"""Conservative CPU structure rules. Never reads annotations, IDs or README."""

import math
import re
import unicodedata

VERSION = "header-conservative-1"
# Generic column-language anchors fixed before dev/check measurement. No BTC names/IDs.
ANCHORS = {
    "id",
    "code",
    "name",
    "date",
    "quantity",
    "qty",
    "price",
    "amount",
    "value",
    "unit",
    "total",
    "time",
    "email",
    "phone",
    "status",
    "note",
    "product",
    "customer",
    "mã",
    "tên",
    "ngày",
    "số",
    "sl",
    "giá",
    "tiền",
    "giờ",
    "đơn vị",
    "đvt",
    "thời gian",
    "trạng thái",
    "ghi chú",
    "tồn",
    "hệ số",
    "quy đổi",
    "điện thoại",
    "hàng",
    "khách",
}


def normalize(value):
    return " ".join(
        unicodedata.normalize("NFC", value).casefold().replace("_", " ").split()
    )


def value_shaped(value):
    t = value.strip()
    return bool(
        t
        and (
            t[0].isdigit()
            or t[0] in "+-"
            and len(t) > 1
            and t[1].isdigit()
            or re.fullmatch(r"[^\W\d_]+[0-9]{2,}", t, re.UNICODE)
            or normalize(t) in {"true", "false"}
        )
    )


def label_like(value):
    return (
        isinstance(value, str)
        and bool(value.strip())
        and any(c.isalpha() for c in value)
        and not value_shaped(value)
    )


def anchored(value):
    n = normalize(value)
    return any(
        re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", n) for word in ANCHORS
    )


def nonempty(row):
    return {int(k): v for k, v in row["v"].items() if v is not None and v != ""}


def candidates(rows, width, *, stronger):
    result = []
    for ix, row in enumerate(rows):
        cells = nonempty(row)
        if len(cells) < max(2, math.ceil(width * 0.75)) or not all(
            label_like(v) for v in cells.values()
        ):
            continue
        following = [r for r in rows[ix + 1 :] if nonempty(r)][:3]
        if len(following) < 2:
            continue
        if sum(len(nonempty(r)) >= max(2, width // 2) for r in following) < 2:
            continue
        if stronger:
            # Require generic label evidence plus independently observable value-shape changes.
            if sum(anchored(v) for v in cells.values()) < 2:
                continue
            changes = [
                sum(
                    value_shaped(v)
                    or (r["m"].get("types", "-") + "-" * width)[i - 1] in "nrb"
                    for i, v in nonempty(r).items()
                    if i in cells
                )
                for r in following
            ]
            if sum(c >= max(1, math.ceil(len(cells) * 0.2)) for c in changes) < 2:
                continue
            repeated = sum(
                any(
                    normalize(v) == normalize(cells[i])
                    for r in following
                    for j, v in nonempty(r).items()
                    if i == j
                )
                for i in cells
            )
            if repeated * 2 >= len(cells):
                continue
        result.append(row["row"])
    return result


def detect(rows, width, *, complete_empty=False, evidence_limited=False, mode="B2"):
    empty = {
        "status": "unresolved",
        "header_rows": [],
        "data_start_row": None,
        "rule_version": VERSION,
        "mode": mode,
        "evidence": {},
    }
    if complete_empty:
        return {**empty, "status": "no_header", "reason": "empty_unit"}
    if evidence_limited:
        return {**empty, "reason": "evidence_byte_limit"}
    if mode == "B0":
        selected = [rows[0]["row"]] if rows else []
    else:
        selected = candidates(rows, width, stronger=mode == "B2")
    empty["evidence"] = {
        "candidate_rows": selected,
        "observed_rows": len(rows),
        "observed_width": width,
    }
    if not selected:
        return {**empty, "reason": "no_safe_candidate"}
    if mode == "B2" and len(selected) != 1:
        return {**empty, "reason": "competing_candidates"}
    leaf = selected[0]
    if mode == "B2":
        reference = {
            i: normalize(v)
            for i, v in nonempty(next(r for r in rows if r["row"] == leaf)).items()
        }
        if (
            sum(
                {i: normalize(v) for i, v in nonempty(r).items()} == reference
                for r in rows
            )
            > 1
        ):
            return {**empty, "reason": "repeated_header_labels"}
    index = next(i for i, r in enumerate(rows) if r["row"] == leaf)
    headers = [leaf]
    # Sparse group labels immediately above the leaf, not a packed title/filter pair.
    if index:
        parent = rows[index - 1]
        cells = nonempty(parent)
        positions = sorted(cells)
        if (
            parent["row"] + 1 == leaf
            and len(cells) >= 2
            and positions[0] == 1
            and positions[-1] >= width / 2
            and positions != list(range(1, len(cells) + 1))
            and all(label_like(v) and ":" not in v for v in cells.values())
        ):
            headers.insert(0, parent["row"])
    data = next((r["row"] for r in rows[index + 1 :] if nonempty(r)), None)
    if data is None:
        return {**empty, "reason": "data_start_not_observed"}
    return {
        **empty,
        "status": "auto_rule",
        "header_rows": headers,
        "data_start_row": data,
        "reason": "dense_labels_and_value_change" if mode == "B2" else "baseline_rule",
    }
