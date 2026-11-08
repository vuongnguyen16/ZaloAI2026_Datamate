"""Explicit reviewed exclusions, restricted to unchanged unfiltered dev sources."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from datamate.prediction_store import regular_bytes
from datamate.scoring import parse_object

from .binding_rules import norm
from .binding_structure import RETURN_QUANTITY, plan_source

METRICS = ("order_count", "revenue_total")
SHA = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Proof(StrictModel):
    index_sha256: SHA
    database_sha256: SHA
    manifest_sha256: SHA
    schema_sha256: SHA
    profile_sha256: SHA


class Receipt(StrictModel):
    state: Literal["approved"]
    reviewer: str = Field(min_length=1, max_length=256)
    reviewed_at: str = Field(min_length=1, max_length=64)
    approval_text: str = Field(min_length=1, max_length=2048)


class ExcludedSource(StrictModel):
    unit: str = Field(pattern=r"^raw_[0-9a-f]{24}$")
    source_file: str = Field(min_length=1, max_length=512)
    source_name: str = Field(min_length=1, max_length=512)
    unit_sha256: SHA
    source_sha256: SHA
    readme_sha256: SHA
    role: Literal["master", "payments"]
    decision: Literal["approved_exclude"]


class ReviewedBusiness(StrictModel):
    business_id: str = Field(min_length=1, max_length=256)
    provenance: Proof
    sources: list[ExcludedSource] = Field(min_length=1, max_length=256)


class SourceReview(StrictModel):
    version: Literal[1]
    kind: Literal["reviewed_source_exclusions"]
    partition: Literal["dev"]
    scope: Literal["default_unfiltered"]
    metrics: list[Literal["order_count", "revenue_total"]] = Field(
        min_length=2, max_length=2
    )
    rulebook_sha256: SHA
    reviewed_packet_sha256: SHA
    review: Receipt
    businesses: list[ReviewedBusiness] = Field(min_length=1, max_length=18)


@dataclass(frozen=True)
class LoadedExclusions:
    artifact: SourceReview
    sha256: str


def unit_digest(unit):
    return hashlib.sha256(
        json.dumps(
            unit,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def load_source_exclusions(
    path, expected_sha256, rulebook_sha256, allowed_businesses, *, now=None
):
    raw = regular_bytes(path, 4 * 1024**2, single_link=True)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha256:
        raise ValueError("source exclusions hash mismatch")
    value = parse_object(raw)
    if value.get("review", {}).get("state") != "approved":
        raise ValueError("human approval receipt required")
    if type(value.get("version")) is not int:
        raise ValueError("invalid review version")
    review = SourceReview.model_validate(value)
    if review.rulebook_sha256 != rulebook_sha256:
        raise ValueError("source exclusions rulebook mismatch")
    if set(review.metrics) != set(METRICS):
        raise ValueError("both unfiltered metrics required")
    if not review.review.reviewer.strip() or not review.review.approval_text.strip():
        raise ValueError("human approval receipt required")
    try:
        at = datetime.fromisoformat(review.review.reviewed_at)
        if at.tzinfo is None or at > (now or datetime.now(timezone.utc)):
            raise ValueError("invalid approval time")
    except ValueError as exc:
        raise ValueError("invalid approval time") from exc
    ids = [b.business_id for b in review.businesses]
    if len(set(ids)) != len(ids) or not set(ids) <= set(allowed_businesses):
        raise ValueError("duplicate or unauthorized dev business")
    for business in review.businesses:
        if len({s.unit for s in business.sources}) != len(business.sources):
            raise ValueError("duplicate reviewed unit")
    return LoadedExclusions(review, digest)


def match_source_exclusions(
    loaded,
    business,
    business_id,
    *,
    scope="default_unfiltered",
    metrics=METRICS,
    filters=(),
):
    """No caller may reuse this receipt to establish filtered capabilities."""
    if scope != "default_unfiltered" or tuple(metrics) != METRICS or filters != ():
        raise ValueError("review permits only both default unfiltered metrics")
    reviewed = next(
        (b for b in loaded.artifact.businesses if b.business_id == business_id), None
    )
    if reviewed is None:
        return {}
    if reviewed.provenance.model_dump() != business.proof:
        raise ValueError("source exclusion provenance mismatch")
    units = {u["sql_name"]: u for u in business.schema["tables"]}
    hashes = {f["path"]: f["sha256"] for f in business.profile["provenance"]["files"]}
    result = {}
    for item in reviewed.sources:
        unit = units.get(item.unit)
        if (
            unit is None
            or item.unit_sha256 != unit_digest(unit)
            or item.source_file != unit["source_file"]
            or item.source_name != unit["source_name"]
            or item.source_sha256 != hashes.get(item.source_file)
            or item.readme_sha256 != hashes.get("README.md")
        ):
            raise ValueError("source exclusion unit/raw/README identity mismatch")
        plan = plan_source(unit, business.readme)
        candidate = getattr(plan, "candidate", None)
        if (
            plan.kind != "unresolved"
            or "event_metadata_requires_review" in getattr(candidate, "reasons", ())
            or any(
                norm(e.get("definition", "")) == RETURN_QUANTITY
                for e in getattr(plan, "evidence", {}).values()
            )
        ):
            raise ValueError("review cannot exclude recognized order/return source")
        result[item.unit] = item
    return result
