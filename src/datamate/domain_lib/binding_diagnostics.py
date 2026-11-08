"""Metric-specific source hypotheses and repetition counts, never approval."""

import hashlib
import json
from collections import defaultdict

from .binding_rules import VERIFIED_HEADERS, header, norm
from .binding_structure import plan_source
from .raw_reader import open_business

METRICS = ("order_count", "revenue_total")


def blocker(reason, *, category="c", unit=None):
    return dict(category=category, reason=reason, unit=unit)


def diagnose_sources(units, readme):
    sources = []
    blocked = {m: [] for m in METRICS}
    plans = [plan_source(u, readme) for u in units]
    joined = any(p.kind == "headers" for p in plans) and any(
        p.kind == "details" for p in plans
    )
    for p in plans:
        c = p.candidate
        name = c.unit["sql_name"]
        pattern = p.pattern
        if p.kind == "unresolved" and c.unit.get("header_status") in VERIFIED_HEADERS:
            signature = sorted(
                (norm(header(col)), norm(p.evidence[col["sql_name"]]["definition"]))
                for col in c.unit["columns"]
            )
            if signature and all(label for label, _ in signature):
                pattern = (
                    "unresolved:"
                    + hashlib.sha256(json.dumps(signature).encode()).hexdigest()[:16]
                )
        sources.append(
            dict(
                unit=name,
                source_file=c.unit["source_file"],
                source_name=c.unit["source_name"],
                kind=p.kind,
                pattern="header_detail"
                if joined and p.kind in {"headers", "details"}
                else pattern,
                evidence=p.evidence,
                reasons=list(c.reasons),
            )
        )
        reasons = []
        if p.kind == "unresolved":
            reasons.extend(blocker(r, unit=name) for r in c.reasons)
            reasons.append(blocker("unresolved_source_role", unit=name))
        if p.kind == "details":
            reasons.append(
                blocker(
                    "header_detail_join" if joined else "missing_verified_header",
                    category="a" if joined else "c",
                    unit=name,
                )
            )
        if p.kind == "return_quantity":
            reasons.append(blocker("return_quantity_event", category="a", unit=name))
        for m in METRICS:
            blocked[m].extend(dict(r) for r in reasons)
        if p.kind in {"combined_lines", "details"} and not c.net_semantics:
            blocked["revenue_total"].append(blocker("net_semantics_missing", unit=name))
    return dict(sources=sources, metric_blockers=blocked, capabilities_granted=False)


def aggregate_patterns(records):
    patterns = defaultdict(lambda: (set(), set()))
    for record in records:
        for source in record["sources"]:
            pattern = source["pattern"]
            if pattern == "unresolved":
                continue
            businesses, clusters = patterns[pattern]
            businesses.add(record["business_id"])
            clusters.add(record["cluster"])
    return {
        p: dict(businesses=len(b), clusters=len(c), rule_eligible=len(b) >= 2)
        for p, (b, c) in sorted(patterns.items())
    }


def attach_repetition(records, patterns):
    """Annotate recurrence without turning an unknown semantic role into a rule."""
    for record in records:
        for source in record.get("sources", []):
            occurrence = patterns.get(source["pattern"])
            source["occurrence"] = occurrence
            if (
                source["kind"] == "unresolved"
                and occurrence
                and occurrence["rule_eligible"]
            ):
                for metric in METRICS:
                    record["metric_blockers"][metric].append(
                        blocker(
                            "repeated_unresolved_structure",
                            category="b",
                            unit=source["unit"],
                        )
                    )


def diagnose_business(index, source, business_id):
    """Schema/README hypotheses only; no raw value, gold or model evaluation."""
    with open_business(index, source, business_id) as business:
        result = diagnose_sources(business.schema["tables"], business.readme)
        result.update(
            business_id=business_id,
            provenance=business.proof,
            count_checked=False,
            revenue_checked=False,
            reason="diagnostic_only",
            candidates=[],
            gold_read=False,
            model_called=False,
            pa_measured=False,
        )
    return result


def blocker_profile(record, metric):
    reasons = {b["reason"] for b in record.get("metric_blockers", {}).get(metric, [])}
    checked = (
        record.get("count_checked" if metric == "order_count" else "revenue_checked")
        is True
    )
    if not reasons and not checked:
        reasons.add(record.get("reason") or "unreported_failure")
    families = set()
    groups = {
        "status": {
            "unknown_status",
            "missing_status_inventory",
            "unknown_order_status",
        },
        "source": {
            "unresolved_source_role",
            "unbound_relevant_source",
            "unbound_order_partition",
            "missing_or_ambiguous_order_columns",
            "conflicting_or_unverified_readme_role",
            "repeated_unresolved_structure",
            "event_metadata_requires_review",
            "no_order_candidate",
            "missing_verified_header",
        },
        "header": {"unresolved_header"},
        "date": {"date_format_unverified", "conflicting_or_missing_order_date"},
        "money": {
            "net_semantics_missing",
            "amount_format_unverified",
            "number_scale_ambiguous",
            "arithmetic_screen_failed",
            "missing_net_amount",
            "missing_order_details",
            "header_without_order_details",
        },
        "resource": {
            "row_resource_or_coordinate",
            "identity_byte_limit",
            "row_byte_limit",
            "worker_timeout",
            "row_resource_limit",
        },
        "structure": {
            "duplicate_order_header",
            "orphan_order_detail",
            "orphan_order_event",
            "unresolved_order_row",
            "missing_group_metadata",
            "ambiguous_order_columns",
            "conflicting_order_status",
        },
    }
    for reason in reasons - {"binding_data_checks_failed"}:
        families.add(
            next(
                (family for family, members in groups.items() if reason in members),
                "other",
            )
        )
    if "binding_data_checks_failed" in reasons and not families:
        families.add("other")
    inspection = record.get("inspection", {})
    unexecuted = []
    if inspection.get("row_scan_complete") is not True:
        unexecuted.append("row_scan")
    if inspection.get("ledger_validated") is not True:
        unexecuted.append("ledger")
    scenarios = {
        "status": {"status"},
        "source": {"source"},
        "status_and_source": {"status", "source"},
    }
    return dict(
        families=sorted(families),
        observed_reasons=sorted(reasons),
        checked=checked,
        unexecuted_checks=unexecuted,
        after_removing={
            name: dict(
                remaining_observed=sorted(families - removed),
                recheck_required=not checked,
                proven_pass=checked,
            )
            for name, removed in scenarios.items()
        },
    )


def summarize_blockers(records):
    result = {}
    for metric in METRICS:
        buckets = {
            "observed_status_only": {"status"},
            "observed_source_only": {"source"},
            "observed_status_and_source_only": {"status", "source"},
        }
        profiles = [(r, blocker_profile(r, metric)) for r in records]
        result[metric] = {
            name: dict(
                businesses=len(
                    {
                        r["business_id"]
                        for r, p in profiles
                        if set(p["families"]) == wanted and not p["checked"]
                    }
                ),
                clusters=len(
                    {
                        r["cluster"]
                        for r, p in profiles
                        if set(p["families"]) == wanted and not p["checked"]
                    }
                ),
            )
            for name, wanted in buckets.items()
        }
        result[metric].update(
            remaining_blocked=dict(
                businesses=len(
                    {
                        r["business_id"]
                        for r, p in profiles
                        if not p["checked"]
                        and set(p["families"]) not in buckets.values()
                    }
                ),
                clusters=len(
                    {
                        r["cluster"]
                        for r, p in profiles
                        if not p["checked"]
                        and set(p["families"]) not in buckets.values()
                    }
                ),
            ),
            is_pass_prediction=False,
            incomplete_inspection=sum(
                bool(p["unexecuted_checks"]) for _, p in profiles
            ),
            already_checked=sum(p["checked"] for _, p in profiles),
        )
    return result
