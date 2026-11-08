"""Dev-only semantic evidence and explicit human-approved literal vocabulary."""

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone

from datamate.prediction_store import regular_bytes
from datamate.proposal_evidence import project_business_readme, project_rulebook
from datamate.scoring import parse_object

from .binding_rules import STATUS, classify_row, norm
from .binding_structure import plan_source
from .model import DomainAbstain


def inventory_business(business, *, max_rows=1000000):
    labels = Counter()
    sources = []
    decisions = []
    rows = 0
    complete = True
    omitted = []
    planned = []
    for unit in business.schema["tables"]:
        plan = plan_source(unit, business.readme)
        spans, projection = project_business_readme(business, unit)
        decisions.append(
            dict(
                unit=unit["sql_name"],
                source_file=unit["source_file"],
                source_name=unit["source_name"],
                source_rows=unit["row_count"],
                proposed_role=plan.kind,
                columns=unit["columns"],
                evidence=spans,
                projection=projection,
                decision="pending",
                reviewed_role="unknown",
                reviewed_column_bindings={},
                reviewed_join=None,
                review_rationale="",
                metric_decisions={
                    m: "pending" for m in ("order_count", "revenue_total")
                },
            )
        )
        planned.append((unit, plan, spans))
    for unit, plan, spans in planned:
        candidate = plan.candidate
        if plan.kind not in {
            "headers",
            "combined_lines",
            "details",
        } or not candidate.columns.get("status"):
            omitted.append(
                dict(unit=unit["sql_name"], reason="not_a_verified_order_status_source")
            )
            continue
        counts = Counter()
        iterator = business.iter_rows(unit)
        try:
            for row in iterator:
                rows += 1
                if rows > max_rows:
                    raise DomainAbstain("inventory_row_budget")
                if classify_row(row, candidate) != "data":
                    continue
                label = (row.cells.get(candidate.columns["status"]) or "").strip()
                if label:
                    if len(label) > 256 or (label not in labels and len(labels) >= 256):
                        raise DomainAbstain("inventory_label_budget")
                    counts[label] += 1
                    labels[label] += 1
        except DomainAbstain as exc:
            complete = False
            omitted.append(dict(unit=unit["sql_name"], reason=exc.code))
        finally:
            iterator.close()
        sources.append(
            dict(
                unit=unit["sql_name"],
                column=candidate.columns["status"],
                labels=dict(counts),
                readme_evidence=spans,
                inventory_complete=business.consumed.get(unit["sql_name"])
                == unit["row_count"],
            )
        )
        if not complete:
            break
    return dict(
        labels=dict(labels),
        status_sources=sources,
        source_decisions=decisions,
        omitted=omitted,
        scanned_rows=min(rows, max_rows),
        inventory_complete=complete,
        inventory_scope="verified order-status columns only; unresolved source roles are not certified",
        provenance=business.proof,
        gold_read=False,
    )


def draft_lexicon(records, rulebook, rulebook_sha256):
    labels = Counter()
    for record in records:
        labels.update(record["labels"])
    spans, meta = project_rulebook(rulebook, "status", rulebook_sha256)
    inventory_sha = hashlib.sha256(
        json.dumps(
            records, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    return dict(
        version=1,
        partition="dev",
        rulebook_sha256=rulebook_sha256,
        inventory_sha256=inventory_sha,
        review=dict(state="pending", reviewer=None, reviewed_at=None),
        entries=[
            dict(
                label=label,
                count=count,
                proposed_target=STATUS.get(
                    norm(label),
                    {
                        k: k for k in ("completed", "shipping", "cancelled", "returned")
                    }.get(norm(label), "unknown"),
                ),
                proposal_basis="Existing conservative lexicon or literal category name; candidate only. Rulebook defines categories, not every synonym.",
                target="unknown",
                decision="pending",
                rulebook_evidence=spans,
                rulebook_projection=meta,
                readme_evidence=[
                    dict(
                        business_id=r["business_id"],
                        unit=s["unit"],
                        column=s["column"],
                        spans=s["readme_evidence"],
                    )
                    for r in records
                    for s in r.get("status_sources", [])
                    if label in s["labels"]
                ],
            )
            for label, count in sorted(labels.items())
        ],
    )


def source_review_packet(records, inventory_sha256, rulebook, rulebook_sha256):
    spans, projection = project_rulebook(rulebook, "source", rulebook_sha256)
    return dict(
        version=1,
        partition="dev",
        review=dict(state="pending", reviewer=None, reviewed_at=None),
        inventory_sha256=inventory_sha256,
        rulebook_sha256=rulebook_sha256,
        rulebook_evidence=spans,
        rulebook_projection=projection,
        businesses=[
            dict(
                business_id=r["business_id"],
                cluster=r["cluster"],
                provenance=r["provenance"],
                sources=r["source_decisions"],
            )
            for r in records
        ],
        control="oracle-binding candidate only; no answer oracle, PA upper-bound or G2 claim",
    )


def load_approved_lexicon(path, expected_sha256, rulebook_sha256, *, now=None):
    raw = regular_bytes(path, 4 * 1024**2, single_link=True)
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("lexicon hash mismatch")
    value = parse_object(raw)
    if (
        value.get("version") != 1
        or value.get("partition") != "dev"
        or value.get("rulebook_sha256") != rulebook_sha256
    ):
        raise ValueError("lexicon scope/rulebook mismatch")
    review = value.get("review", {})
    if (
        review.get("state") != "approved"
        or not isinstance(review.get("reviewer"), str)
        or not review["reviewer"].strip()
    ):
        raise ValueError("human approval receipt required")
    try:
        at = datetime.fromisoformat(review["reviewed_at"])
        if at.tzinfo is None or at > (now or datetime.now(timezone.utc)):
            raise ValueError("invalid approval time")
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid approval time") from exc
    entries = value.get("entries")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 256:
        raise ValueError("bounded lexicon entries required")
    result = {}
    for entry in entries:
        label = entry.get("label")
        target = entry.get("target")
        decision = entry.get("decision")
        if not isinstance(label, str) or not label or len(label) > 256:
            raise ValueError("invalid literal label")
        if not (
            (
                decision == "approved"
                and target in {"completed", "shipping", "cancelled", "returned"}
            )
            or (decision == "unknown" and target == "unknown")
        ):
            raise ValueError("pending/invalid entry is not approval")
        key = norm(label)
        mapped = None if target == "unknown" else target
        if (key in result and result[key] != mapped) or (
            key in STATUS and mapped is not None and STATUS[key] != mapped
        ):
            raise ValueError("conflicting reviewed status mapping")
        result[key] = mapped
    return result
