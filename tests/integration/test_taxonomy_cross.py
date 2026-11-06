import copy
import json
from pathlib import Path

import pytest

from datamate.artifacts import sha256
from datamate.taxonomy import classify
from datamate.taxonomy_cross import cross_table, run_taxonomy_cross
from tests.integration.test_evaluation import scoped_fixture as scoped_fixture
from tests.integration.test_evaluation import selected

ROOT = Path(__file__).resolve().parents[2]


def record(qid, operations, times):
    return dict(
        id=qid,
        family="sales",
        operations=operations,
        expected_type="number",
        time_forms=times,
    )


def test_cartesian_counts_distinguish_questions_from_memberships():
    result = cross_table(
        [
            record("a", ["sum", "count"], ["month", "year"]),
            record("b", ["sum"], ["month"]),
        ]
    )
    assert result["unique_questions"] == 2
    assert result["memberships"] == 5
    assert len(result["cells"]) == 4
    assert (
        next(
            c
            for c in result["cells"]
            if c["operation"] == "sum" and c["time_form"] == "month"
        )["count"]
        == 2
    )
    with pytest.raises(ValueError, match="duplicate"):
        cross_table([record("a", ["sum"], ["month"])] * 2)


@pytest.fixture
def pinned(scoped_fixture, tmp_path):
    source, split, digest, manifest, _ = scoped_fixture
    rules = ROOT / "configs/taxonomy_rules.json"
    labels = json.loads(rules.read_text("utf-8"))
    records = [
        dict(
            id=qid,
            business_id=manifest["source"]["questions"][qid],
            **classify("Synthetic sales this month", "number", labels),
        )
        for qid in sorted(selected(manifest, "dev"))
    ]
    path = tmp_path / "taxonomy.json"
    path.write_text(
        json.dumps(
            dict(
                valid=True,
                partition="dev",
                manifest_sha256=digest,
                rules_sha256=sha256(rules),
                implementation_sha256=sha256(ROOT / "src/datamate/taxonomy.py"),
                records=records,
            )
        ),
        encoding="utf-8",
    )
    proof = dict(
        split_manifest_sha256=digest,
        taxonomy_rules=dict(path=str(rules), sha256=sha256(rules)),
        artifacts=[dict(path=str(path), sha256=sha256(path))],
    )
    return source, split, digest, path, proof


def test_pinned_dev_reader_never_opens_gold(pinned, tmp_path, monkeypatch):
    source, split, digest, path, proof = pinned
    original = Path.open

    def guard(self, *args, **kwargs):
        assert self.name != "answers.jsonl", "must not open gold even for routing"
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guard)
    result = run_taxonomy_cross(split, digest, tmp_path / "out", proof=proof)
    assert result["valid"] and not result["gold_content_read"]
    raw = (tmp_path / "out/cross.json").read_text("utf-8")
    assert "synthetic_q" not in raw and "business_id" not in raw


def test_hash_checked_before_taxonomy_decode(pinned, tmp_path, monkeypatch):
    _, split, digest, path, proof = pinned
    path.write_bytes(b"MUST NOT DECODE")
    import datamate.taxonomy_cross as module

    real = module.parse_object

    def guard(raw):
        assert raw != b"MUST NOT DECODE"
        return real(raw)

    monkeypatch.setattr(module, "parse_object", guard)
    with pytest.raises(ValueError, match="hash"):
        run_taxonomy_cross(split, digest, tmp_path / "out", proof=proof)


@pytest.mark.parametrize(
    "mutation", ["duplicate", "scope", "gold", "implementation", "proof"]
)
def test_rejects_scope_duplicates_source_and_unknown_fields(pinned, tmp_path, mutation):
    _, split, digest, path, proof = pinned
    obj = json.loads(path.read_text("utf-8"))
    if mutation == "duplicate":
        obj["records"].append(copy.deepcopy(obj["records"][0]))
    elif mutation == "scope":
        obj["records"][0]["id"] = "synthetic_sealed"
    elif mutation == "gold":
        obj["records"][0]["answer"] = "FORBIDDEN"
    elif mutation == "implementation":
        obj["implementation_sha256"] = "0" * 64
    else:
        proof["split_manifest_sha256"] = "0" * 64
    path.write_text(json.dumps(obj), encoding="utf-8")
    proof["artifacts"][0]["sha256"] = sha256(path)
    with pytest.raises(ValueError):
        run_taxonomy_cross(split, digest, tmp_path / "out", proof=proof)
