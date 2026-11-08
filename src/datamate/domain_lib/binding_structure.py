"""Closed semantic source plans; hypotheses never confer business approval."""

from dataclasses import dataclass, replace

from .binding_rules import (
    ROLES,
    VERIFIED_HEADERS,
    Candidate,
    definitions,
    header,
    norm,
    propose,
)

RETURN_QUANTITY = norm(
    "số lượng khách trả lại (đơn vị cơ bản); lớn hơn 0: đơn đó có trả hàng"
)
CONVERSION_MEANINGS = {
    "product": {
        norm("tên hàng (file chỉ có mặt hàng có đơn vị lớn)"),
        norm("tên hàng"),
        norm("mã hàng"),
    },
    "large_unit": {norm("đơn vị lớn (thùng, hộp, tấn...)")},
    "factor": {norm("hệ số: số đơn vị cơ bản trong 1 đơn vị lớn")},
    "base_unit": {norm("đơn vị cơ bản")},
}


@dataclass(frozen=True)
class SourcePlan:
    candidate: Candidate
    kind: str
    pattern: str
    evidence: dict


def plan_source(unit, readme):
    candidate = propose(unit, readme)
    dictionary = definitions(readme).get(unit["source_file"].casefold(), {})
    evidence = {
        c["sql_name"]: dict(
            label=header(c), definition=dictionary.get(norm(header(c)), "")
        )
        for c in unit["columns"]
    }
    meanings = {c: norm(e["definition"]) for c, e in evidence.items()}
    verified = (
        unit.get("header_status") in VERIFIED_HEADERS
        and unit.get("data_start_row") is not None
    )
    # Exclusion requires the entire declared schema to have positively known
    # conversion meanings. No missing-date/no-key inference, or filename rule.
    allowed = set().union(*CONVERSION_MEANINGS.values())
    compatible = True
    for column, meaning in meanings.items():
        label = norm(evidence[column]["label"])
        roles = {r for r, terms in ROLES.items() if label in terms}
        if (
            roles
            and not (roles == {"product"} and meaning in CONVERSION_MEANINGS["product"])
        ) or label in {"thanhtien", "tongtien", "netline", "net"}:
            compatible = False
    if (
        verified
        and meanings
        and compatible
        and all(v in allowed for v in meanings.values())
        and all(
            any(v in choices for v in meanings.values())
            for choices in CONVERSION_MEANINGS.values()
        )
    ):
        return SourcePlan(candidate, "conversion", "conversion_dictionary", evidence)
    returns = [c for c, v in meanings.items() if v == RETURN_QUANTITY]
    if returns and (
        candidate.columns.get("day")
        or candidate.columns.get("status")
        or "ambiguous_order_columns" in candidate.reasons
    ):
        return SourcePlan(
            replace(
                candidate,
                reasons=candidate.reasons + ("event_metadata_requires_review",),
            ),
            "unresolved",
            "unresolved",
            evidence,
        )
    if (
        verified
        and "id" in candidate.columns
        and len(returns) == 1
        and "conflicting_or_unverified_readme_role" not in candidate.reasons
    ):
        candidate = replace(
            candidate,
            role="events",
            columns={"id": candidate.columns["id"], "return_qty": returns[0]},
            reasons=(),
        )
        return SourcePlan(candidate, "return_quantity", "return_quantity", evidence)
    if not candidate.reasons:
        kind = "combined_lines" if candidate.role == "lines" else "headers"
        return SourcePlan(candidate, kind, kind, evidence)
    product_ids = [c for c, v in meanings.items() if v == norm("mã hàng")]
    line_markers = bool(candidate.columns.get("product") or product_ids)
    # Recognize detail rows without fabricating absent day/status columns.
    # The caller must require an actual verified header join and cover all IDs.
    if (
        verified
        and "id" in candidate.columns
        and line_markers
        and (candidate.columns.get("amount") or candidate.columns.get("qty"))
        and set(candidate.reasons) <= {"missing_or_ambiguous_order_columns"}
    ):
        candidate = replace(candidate, role="lines", reasons=())
        return SourcePlan(candidate, "details", "header_detail", evidence)
    return SourcePlan(candidate, "unresolved", "unresolved", evidence)
