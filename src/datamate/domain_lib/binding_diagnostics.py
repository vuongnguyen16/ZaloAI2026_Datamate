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
