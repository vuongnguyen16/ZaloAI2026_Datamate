"""Leakage/access regressions using only generated synthetic businesses."""

import json
import sqlite3
from pathlib import Path
from zipfile import ZipFile

import pytest

from datamate.artifacts import sha256
from datamate.splits import (
    assign,
    authorize_access,
    catalog,
    encoded,
    freeze_split,
    header_template,
    log_public_submission,
    open_split,
    read_ledger,
)

ROOT = Path(__file__).resolve().parents[2]
H = "a" * 64


@pytest.fixture
def dataset(tmp_path):
    source = tmp_path / "train"
    source.mkdir()
    records, questions = [], []
    for i in range(8):
        bid = f"synthetic_{i}"
        business = source / "data" / bid
        business.mkdir(parents=True)
        intro = "Shared layout" if i in (4, 5) else f"Unique layout {i}"
        (business / "README.md").write_text(f"# Data\n\n{intro}\n", encoding="utf-8")
        headers = ["key0"] if i == 1 else [f"key{i}"]
        if i == 1:
            headers.append("key2")
        for j, header in enumerate(headers):
            path = business / f"table{j}.csv"
            path.write_text(f"{header},quantity\nvalue_{i},{i}\n", encoding="utf-8")
            template = header_template([header, "quantity"])
            records.append(
                dict(
                    business_id=bid,
                    source_file=path.name,
                    source_name=path.stem,
                    source_sha256=sha256(path),
                    readme_sha256=sha256(business / "README.md"),
                    template=template,
                    group=template,
                )
            )
        questions.append(
            dict(
                id=f"q{i}",
                business_id=bid,
                question="Synthetic question",
                as_of_date="2026-01-01",
            )
        )
    (source / "questions.jsonl").write_text(
        "".join(json.dumps(q) + "\n" for q in questions), encoding="utf-8"
    )
    (source / "rulebook.md").write_text("Synthetic rules", encoding="utf-8")
    (source / "calendar.csv").write_text(
        "date,event\n2026-01-01,synthetic\n", encoding="utf-8"
    )
    (source / "answers.jsonl").write_text("GOLD MUST NOT BE OPENED", encoding="utf-8")
    labels = tmp_path / "labels.json"
    labels.write_bytes(encoded(dict(records=records)))
    policy = tmp_path / "policy.json"
    policy.write_bytes((ROOT / "configs/split_policy.json").read_bytes())
    return source, labels, policy


def freeze(dataset, path):
    source, labels, policy = dataset
    return freeze_split(source, labels, sha256(labels), policy, path)


def test_frozen_split_is_deterministic_transitive_and_never_opens_gold(
    dataset, tmp_path, monkeypatch
):
    source, labels, policy = dataset
    original = Path.open

    def no_gold(path, *args, **kwargs):
        if path.name == "answers.jsonl":
            raise AssertionError("Gold must never be opened")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", no_gold)
    first = freeze(dataset, tmp_path / "first")
    second = freeze(dataset, tmp_path / "second")
    assert first["manifest_sha256"] == second["manifest_sha256"]
    manifest, _ = open_split(
        tmp_path / "first", first["manifest_sha256"], verify_sources=True
    )
    alloc = manifest["business_partitions"]
    assert alloc["synthetic_0"] == alloc["synthetic_1"] == alloc["synthetic_2"]
    assert alloc["synthetic_4"] == alloc["synthetic_5"]
    assert sum(r["questions"] for r in first["summary"].values()) == 8
    assert all(r["businesses"] > 0 for r in first["summary"].values())
    info = catalog(source, labels, sha256(labels))
    choices = assign(info, json.loads(policy.read_text("utf-8")))[0]
    info["signatures"].reverse()
    info["layouts"] = dict(reversed(list(info["layouts"].items())))
    assert assign(info, json.loads(policy.read_text("utf-8")))[0] == choices


@pytest.mark.parametrize(
    "failure",
    [
        "duplicate_question",
        "missing_unit",
        "stale_label",
        "single_component",
        "labels_hash",
    ],
)
def test_bad_evidence_fails_before_creating_output(dataset, tmp_path, failure):
    source, labels, policy = dataset
    expected = sha256(labels)
    if failure == "duplicate_question":
        q = source / "questions.jsonl"
        q.write_text(
            q.read_text("utf-8") + q.read_text("utf-8").splitlines()[0] + "\n",
            encoding="utf-8",
        )
    else:
        obj = json.loads(labels.read_text("utf-8"))
        if failure == "missing_unit":
            obj["records"].pop()
        elif failure == "stale_label":
            obj["records"][0]["source_sha256"] = H
        elif failure == "single_component":
            for r in obj["records"]:
                r["template"] = H
        else:
            expected = H
        labels.write_bytes(encoded(obj))
        if failure != "labels_hash":
            expected = sha256(labels)
    output = tmp_path / "not-created"
    with pytest.raises(ValueError):
        freeze_split(source, labels, expected, policy, output)
    assert not output.exists()


@pytest.mark.parametrize("failure", ["inside", "ancestor", "existing", "public"])
def test_freeze_protects_source_and_output(dataset, tmp_path, failure):
    source, labels, policy = dataset
    target = {
        "inside": source / "bad",
        "ancestor": tmp_path,
        "existing": tmp_path / "existing",
        "public": tmp_path / "output",
    }[failure]
    if failure == "existing":
        target.mkdir()
    if failure == "public":
        public = source.with_name("public")
        source.rename(public)
        source = public
    with pytest.raises(ValueError):
        freeze_split(source, labels, sha256(labels), policy, target)


@pytest.mark.parametrize("failure", ["manifest", "policy", "raw", "ledger"])
def test_use_refuses_tampered_or_stale_artifacts(dataset, tmp_path, failure):
    output = tmp_path / "frozen"
    r = freeze(dataset, output)
    if failure in {"manifest", "policy"}:
        p = output / f"{failure}.json"
        p.write_bytes(p.read_bytes() + b" ")
    elif failure == "raw":
        (dataset[0] / "data/synthetic_0/table0.csv").write_text(
            "changed", encoding="utf-8"
        )
    else:
        (output / "access.jsonl").write_text("{}\n", encoding="utf-8")
    with pytest.raises((ValueError, KeyError)):
        open_split(output, r["manifest_sha256"], verify_sources=True)


def test_access_requires_correct_role_and_never_releases_holdout_gold(
    dataset, tmp_path
):
    output = tmp_path / "frozen"
    r = freeze(dataset, output)

    def access(partition, resource, purpose, actor):
        return authorize_access(
            output, r["manifest_sha256"], partition, resource, purpose, actor, H
        )

    assert access("dev", "gold", "taxonomy", "developer")
    assert access("calibration", "gold", "calibration", "evaluator")
    assert access("holdout", "questions", "frozen_inference", "inference")
    for args in [
        ("dev", "gold", "evaluation", "inference"),
        ("calibration", "gold", "calibration", "developer"),
        ("calibration", "gold", "training", "evaluator"),
        ("holdout", "gold", "evaluation", "evaluator"),
        ("holdout", "gold", "P7", "evaluator"),
        ("holdout", "questions", "development", "developer"),
    ]:
        with pytest.raises(PermissionError):
            access(*args)
    events = read_ledger(output / "access.jsonl")
    assert len(events) == 9 and all(e["gold_content_read"] is False for e in events)
    assert sum(e["allowed"] for e in events) == 3
    # Hash chaining survives multiple requests; editing an existing event is detected.
    p = output / "access.jsonl"
    p.write_text(
        p.read_text("utf-8").replace('"allowed": false', '"allowed": true', 1),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="corrupt"):
        read_ledger(p)


def test_public_audit_forbids_tuning_duplicates_and_concurrent_writer(
    dataset, tmp_path
):
    output = tmp_path / "frozen"
    r = freeze(dataset, output)

    def log(phase="P2", purpose="format", submission=H):
        log_public_submission(
            output,
            r["manifest_sha256"],
            phase,
            purpose,
            H,
            submission,
            "Synthetic receipt and verified quota",
        )

    log()
    for kwargs in [
        {},
        {"submission": "b" * 64},
        {"phase": "P3", "purpose": "threshold"},
        {"phase": "P0"},
    ]:
        with pytest.raises(ValueError):
            log(**kwargs)
    busy = output / ".ledger-operation.lock"
    busy.write_text("synthetic competing writer", encoding="utf-8")
    with pytest.raises(ValueError, match="busy"):
        log(phase="P3", submission="b" * 64)
    assert busy.exists()
    assert len(read_ledger(output / "public_submissions.jsonl")) == 1


def test_sqlite_schema_only_is_counted_without_modifying_database(dataset, tmp_path):
    path = dataset[0] / "data/synthetic_3/source.sqlite"
    with sqlite3.connect(path) as db:
        db.execute(
            'CREATE TABLE "synthetic_table" (unique_sqlite_key TEXT, amount INTEGER)'
        )
        db.execute("INSERT INTO synthetic_table VALUES ('synthetic', 2)")
    before = sha256(path)
    result = freeze(dataset, tmp_path / "frozen")
    manifest, _ = open_split(
        tmp_path / "frozen", result["manifest_sha256"], verify_sources=True
    )
    assert manifest["source"]["sqlite_units"] == 1
    assert sha256(path) == before


def test_all_workbook_sheets_must_have_source_bound_structural_labels(
    dataset, tmp_path
):
    source, labels, _ = dataset
    path = source / "data/synthetic_7/book.xlsx"
    with ZipFile(path, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets><sheet name="One"/><sheet name="Two"/></sheets></workbook>',
        )
    obj = json.loads(labels.read_text("utf-8"))
    record = dict(
        business_id="synthetic_7",
        source_file="book.xlsx",
        source_name="One",
        source_sha256=sha256(path),
        readme_sha256=sha256(path.parent / "README.md"),
        template=H,
        group=H,
    )
    obj["records"].append(record)
    labels.write_bytes(encoded(obj))
    with pytest.raises(ValueError, match="every source unit"):
        freeze(dataset, tmp_path / "bad")
    obj["records"].append(dict(record, source_name="Two"))
    labels.write_bytes(encoded(obj))
    assert freeze(dataset, tmp_path / "good")["valid"]
