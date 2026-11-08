import copy
import hashlib
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from datamate.domain_lib.source_exclusions import (
    load_source_exclusions,
    match_source_exclusions,
    unit_digest,
)


def source_unit():
    return dict(
        sql_name="raw_" + "1" * 24,
        source_file="catalog.csv",
        source_name="catalog",
        columns=[],
        row_count=3,
    )


def artifact():
    unit = source_unit()
    proof = {
        k: "a" * 64
        for k in (
            "index_sha256",
            "database_sha256",
            "manifest_sha256",
            "schema_sha256",
            "profile_sha256",
        )
    }
    return dict(
        version=1,
        kind="reviewed_source_exclusions",
        partition="dev",
        scope="default_unfiltered",
        metrics=["order_count", "revenue_total"],
        rulebook_sha256="b" * 64,
        reviewed_packet_sha256="c" * 64,
        review=dict(
            state="approved",
            reviewer="human owner",
            reviewed_at="2026-11-08T00:00:00+00:00",
            approval_text="Approve exact scoped exclusions",
        ),
        businesses=[
            dict(
                business_id="synthetic",
                provenance=proof,
                sources=[
                    dict(
                        unit=unit["sql_name"],
                        source_file=unit["source_file"],
                        source_name=unit["source_name"],
                        unit_sha256=unit_digest(unit),
                        source_sha256="d" * 64,
                        readme_sha256="e" * 64,
                        role="master",
                        decision="approved_exclude",
                    )
                ],
            )
        ],
    )


def load(tmp_path, value=None, **kwargs):
    path = tmp_path / "review.json"
    path.write_text(json.dumps(value or artifact()), encoding="utf-8")
    return load_source_exclusions(
        path,
        hashlib.sha256(path.read_bytes()).hexdigest(),
        "b" * 64,
        {"synthetic"},
        now=datetime(2026, 11, 8, 1, tzinfo=timezone.utc),
        **kwargs,
    )


def business(value=None):
    value = value or artifact()
    return SimpleNamespace(
        schema=dict(tables=[source_unit()]),
        readme="untrusted",
        proof=value["businesses"][0]["provenance"],
        profile=dict(
            provenance=dict(
                files=[
                    dict(path="catalog.csv", sha256="d" * 64),
                    dict(path="README.md", sha256="e" * 64),
                ]
            )
        ),
    )


def test_exact_review_matches_only_business_unit_and_unfiltered_both_metrics(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "datamate.domain_lib.source_exclusions.plan_source",
        lambda *a: SimpleNamespace(kind="unresolved"),
    )
    review = load(tmp_path)
    matches = match_source_exclusions(review, business(), "synthetic")
    assert set(matches) == {source_unit()["sql_name"]}
    assert match_source_exclusions(review, business(), "other") == {}
    for kwargs in [
        dict(scope="filtered"),
        dict(filters=("customer",)),
        dict(metrics=("order_count",)),
    ]:
        with pytest.raises(ValueError):
            match_source_exclusions(review, business(), "synthetic", **kwargs)


@pytest.mark.parametrize(
    "change",
    [
        lambda v: v["review"].update(state="pending"),
        lambda v: v["review"].update(reviewed_at="2099-01-01T00:00:00+00:00"),
        lambda v: v.update(partition="calibration"),
        lambda v: v.update(scope="all_filters"),
        lambda v: v.update(metrics=["order_count"]),
        lambda v: v["businesses"][0].update(business_id="sealed"),
        lambda v: v["businesses"][0]["sources"][0].update(role="events"),
        lambda v: v["businesses"][0]["sources"].append(
            copy.deepcopy(v["businesses"][0]["sources"][0])
        ),
        lambda v: v["businesses"].append(copy.deepcopy(v["businesses"][0])),
    ],
)
def test_pending_stale_scope_metric_role_duplicate_and_nondev_rejected(
    tmp_path, change
):
    value = artifact()
    change(value)
    with pytest.raises(ValueError):
        load(tmp_path, value)


def test_hash_and_rulebook_mismatch_rejected(tmp_path):
    path = tmp_path / "review.json"
    path.write_text(json.dumps(artifact()), encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        load_source_exclusions(path, "0" * 64, "b" * 64, {"synthetic"})
    with pytest.raises(ValueError):
        load_source_exclusions(path, digest, "0" * 64, {"synthetic"})


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b.proof.update(database_sha256="f" * 64),
        lambda b: b.schema["tables"][0].update(row_count=4),
        lambda b: b.profile["provenance"]["files"][0].update(sha256="f" * 64),
        lambda b: b.profile["provenance"]["files"][1].update(sha256="f" * 64),
        lambda b: b.schema.update(tables=[]),
    ],
)
def test_identity_drift_and_missing_unit_never_reuse_approval(
    tmp_path, monkeypatch, change
):
    monkeypatch.setattr(
        "datamate.domain_lib.source_exclusions.plan_source",
        lambda *a: SimpleNamespace(kind="unresolved"),
    )
    review = load(tmp_path)
    current = business()
    change(current)
    with pytest.raises(ValueError):
        match_source_exclusions(review, current, "synthetic")


@pytest.mark.parametrize(
    "kind", ["headers", "combined_lines", "details", "return_quantity", "conversion"]
)
def test_review_cannot_exclude_known_order_or_return_plan(tmp_path, monkeypatch, kind):
    monkeypatch.setattr(
        "datamate.domain_lib.source_exclusions.plan_source",
        lambda *a: SimpleNamespace(kind=kind),
    )
    review = load(tmp_path)
    with pytest.raises(ValueError):
        match_source_exclusions(review, business(), "synthetic")
