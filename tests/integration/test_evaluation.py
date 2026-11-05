import json
from pathlib import Path

import pytest

from datamate.artifacts import sha256
from datamate.evaluation import run_eval
from datamate.scoped_data import project_id, read_scoped
from datamate.splits import encoded, freeze_split, header_template, open_split
from datamate.taxonomy import classify, run_taxonomy

ROOT = Path(__file__).resolve().parents[2]
H = "b" * 64


@pytest.fixture
def scoped_fixture(tmp_path):
    source = tmp_path / "train"
    labels = []
    questions = []
    for i in range(6):
        bid = f"synthetic_{i}"
        business = source / "data" / bid
        business.mkdir(parents=True)
        (business / "README.md").write_text(
            f"# Synthetic\n\nLayout {i}\n", encoding="utf-8"
        )
        table = business / "data.csv"
        table.write_text(f"unique_{i},qty\nA,{i}\n", encoding="utf-8")
        template = header_template([f"unique_{i}", "qty"])
        labels.append(
            dict(
                business_id=bid,
                source_file="data.csv",
                source_name="data",
                source_sha256=sha256(table),
                readme_sha256=sha256(business / "README.md"),
                template=template,
                group=template,
            )
        )
        for j in range(3):
            questions.append(
                dict(
                    id=f"synthetic_q{i}_{j}",
                    business_id=bid,
                    question="Doanh thu tháng này là bao nhiêu?",
                    as_of_date="2026-01-01",
                )
            )
    (source / "questions.jsonl").write_text(
        "".join(json.dumps(q, ensure_ascii=False) + "\n" for q in questions),
        encoding="utf-8",
    )
    (source / "rulebook.md").write_text("Synthetic rules", encoding="utf-8")
    (source / "calendar.csv").write_text(
        "date,event\n2026-01-01,synthetic\n", encoding="utf-8"
    )
    lp = tmp_path / "labels.json"
    lp.write_bytes(encoded(dict(records=labels)))
    policy = tmp_path / "split_policy.json"
    policy.write_bytes((ROOT / "configs/split_policy.json").read_bytes())
    split = tmp_path / "split"
    frozen = freeze_split(source, lp, sha256(lp), policy, split)
    manifest, _ = open_split(split, frozen["manifest_sha256"])
    gold = [
        dict(answer=i + 1, id=q["id"], type="number", alias=[])
        for i, q in enumerate(questions)
    ]
    gp = source / "answers.jsonl"
    gp.write_text("".join(json.dumps(g) + "\n" for g in gold), encoding="utf-8")
    return source, split, frozen["manifest_sha256"], manifest, gold


def selected(manifest, partition):
    return {
        q
        for q, b in manifest["source"]["questions"].items()
        if manifest["business_partitions"][b] == partition
    }


def test_gold_reader_only_decodes_authorized_values_even_when_id_is_last(
    scoped_fixture, monkeypatch
):
    source, split, digest, manifest, gold = scoped_fixture
    ids = selected(manifest, "dev")
    opaque = [
        g
        if g["id"] in ids
        else dict(answer={"CANARY": "DO_NOT_DECODE"}, type="FORBIDDEN", id=g["id"])
        for g in gold
    ]
    (source / "answers.jsonl").write_text(
        "".join(json.dumps(g) + "\n" for g in opaque), encoding="utf-8"
    )
    import datamate.scoped_data as reader

    original = reader.parse_object
    decoded = []

    def spy(raw):
        qid = project_id(raw)
        assert qid in ids
        decoded.append(qid)
        return original(raw)

    monkeypatch.setattr(reader, "parse_object", spy)
    data, audit = read_scoped(
        split, digest, "dev", "gold", "evaluation", "evaluator", H
    )
    assert set(data) == set(decoded) == ids
    assert audit["decoded_records"] == len(ids) and audit[
        "skipped_value_records"
    ] == 18 - len(ids)


@pytest.mark.parametrize(
    "partition,actor,purpose",
    [
        ("holdout", "evaluator", "evaluation"),
        ("holdout", "evaluator", "P7"),
        ("calibration", "developer", "taxonomy"),
        ("dev", "inference", "evaluation"),
    ],
)
def test_gold_denied_before_file_open(
    scoped_fixture, monkeypatch, partition, actor, purpose
):
    _, split, digest, _, _ = scoped_fixture
    original = Path.open

    def no_gold(path, *args, **kwargs):
        if path.name == "answers.jsonl":
            raise AssertionError("Denied gold must never be opened")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", no_gold)
    with pytest.raises(PermissionError):
        read_scoped(split, digest, partition, "gold", purpose, actor, H)


def test_run_eval_contract_counts_control_and_no_answer_export(
    scoped_fixture, tmp_path
):
    _, split, digest, manifest, gold = scoped_fixture
    ids = sorted(selected(manifest, "dev"))
    pred = [
        {k: v for k, v in g.items() if k != "alias"} for g in gold if g["id"] in ids[2:]
    ]
    pred.append(dict(id=ids[0], type="number", answer=-999))
    candidate = tmp_path / "submission.jsonl"
    candidate.write_text("".join(json.dumps(r) + "\n" for r in pred), encoding="utf-8")
    control = tmp_path / "control.jsonl"
    control.write_bytes(b"")
    result = run_eval(
        split,
        digest,
        "dev",
        candidate,
        tmp_path / "eval",
        ROOT / "configs/scoring_policy.json",
        control=control,
    )
    assert result["summary"] == dict(
        n=len(ids),
        correct=len(ids) - 2,
        wrong=1,
        abstain=1,
        pa=(len(ids) - 3) / len(ids),
    )
    assert result["comparison"]["delta_pa"] == result["summary"]["pa"]
    assert result["new_errors_count"] == 1
    rows = [
        json.loads(line)
        for line in (tmp_path / "eval/per_question.jsonl")
        .read_text("utf-8")
        .splitlines()
    ]
    assert len(rows) == len(ids) and all(
        "answer" not in r and "alias" not in r for r in rows
    )
    assert not result["runtime"]["inference_available"]


def test_calibration_exports_aggregates_and_taxonomy_is_dev_only(
    scoped_fixture, tmp_path
):
    _, split, digest, manifest, _ = scoped_fixture
    empty = tmp_path / "empty.jsonl"
    empty.write_bytes(b"")
    result = run_eval(
        split,
        digest,
        "calibration",
        empty,
        tmp_path / "cal",
        ROOT / "configs/scoring_policy.json",
    )
    assert result["summary"]["abstain"] == len(selected(manifest, "calibration"))
    assert not (tmp_path / "cal/per_question.jsonl").exists()
    taxonomy = run_taxonomy(
        split, digest, ROOT / "configs/taxonomy_rules.json", tmp_path / "taxonomy"
    )
    assert taxonomy["coverage"]["classified"] == len(selected(manifest, "dev"))
    assert taxonomy["coverage"]["train_metadata"] == 18
    assert taxonomy["summary"]["by_family"] == {
        "revenue": len(selected(manifest, "dev"))
    }
    assert taxonomy["summary"]["by_time_form"] == {
        "relative_month": len(selected(manifest, "dev"))
    }


@pytest.mark.parametrize(
    "kind", ["unknown_id", "duplicate_id", "bad_json", "output_overlap"]
)
def test_invalid_eval_fails_before_gold(scoped_fixture, tmp_path, monkeypatch, kind):
    source, split, digest, manifest, _ = scoped_fixture
    qid = next(iter(selected(manifest, "dev")))
    raw = json.dumps(dict(id=qid, type="abstain")) + "\n"
    candidate = tmp_path / "predictions.jsonl"
    candidate.write_text(
        raw + raw
        if kind == "duplicate_id"
        else "{broken\n"
        if kind == "bad_json"
        else json.dumps(dict(id="unknown", type="abstain")) + "\n"
        if kind == "unknown_id"
        else raw,
        encoding="utf-8",
    )
    original = Path.open

    def no_gold(path, *args, **kwargs):
        if path.name == "answers.jsonl":
            raise AssertionError("Invalid run must fail before gold")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", no_gold)
    with pytest.raises(ValueError):
        run_eval(
            split,
            digest,
            "dev",
            candidate,
            source / "bad" if kind == "output_overlap" else tmp_path / "out",
            ROOT / "configs/scoring_policy.json",
        )


@pytest.mark.parametrize(
    "raw",
    [
        b'{"id":"x","id":"y"}',
        b'{"id":"x",}',
        b'{"id":{}}',
        b'{"id":"x","a":NaN}',
        b"[]",
    ],
)
def test_projection_rejects_ambiguous_envelopes(raw):
    with pytest.raises(ValueError):
        project_id(raw)


def test_taxonomy_normalization_time_and_ambiguity():
    rules = json.loads((ROOT / "configs/taxonomy_rules.json").read_text("utf-8"))
    a = classify(
        "Top 5 SP doanh thu cao nhất trong 7 ngày gần nhất so với cùng kỳ năm ngoái?",
        "list",
        rules,
    )
    assert a["family"] == "revenue" and a["ambiguous_family"]
    assert {"ranking", "comparison"} <= set(a["operations"])
    assert {"rolling_window", "same_period", "relative_year"} <= set(a["time_forms"])
    assert a["abbreviations"] == ["sp"]
    assert classify("doanh thu thang nay", "number", rules)["family"] == "revenue"


def test_taxonomy_handles_dev_language_motifs_without_answer_values():
    rules = json.loads((ROOT / "configs/taxonomy_rules.json").read_text("utf-8"))
    result = classify("hqua dthu la bnhiu, loai don huy?", "number", rules)
    assert result["family"] == "revenue" and "relative_day" in result["time_forms"]
    assert {"dthu", "hqua", "bnhiu"} <= set(result["abbreviations"])
    assert classify("soos bill hqua la bn", "number", rules)["family"] == "order_count"
    assert classify("tong cong may ly ban ra?", "number", rules)["family"] == "quantity"


def test_taxonomy_execution_metadata_and_failed_read_audit(scoped_fixture, tmp_path):
    from datamate.splits import read_ledger

    source, split, digest, manifest, gold = scoped_fixture
    tax = tmp_path / "taxonomy"
    run_taxonomy(split, digest, ROOT / "configs/taxonomy_rules.json", tax)
    ids = selected(manifest, "dev")
    execution = tmp_path / "events.jsonl"
    execution.write_text(
        "".join(
            json.dumps(dict(id=q, route="synthetic", duration_seconds=0.125)) + "\n"
            for q in ids
        ),
        encoding="utf-8",
    )
    empty = tmp_path / "empty.jsonl"
    empty.write_bytes(b"")
    result = run_eval(
        split,
        digest,
        "dev",
        empty,
        tmp_path / "with-metadata",
        ROOT / "configs/scoring_policy.json",
        taxonomy=tax / "taxonomy.json",
        execution=execution,
    )
    assert result["by_family"]["revenue"]["n"] == len(ids)
    assert (
        result["runtime"]["inference_available"]
        and result["runtime"]["inference_seconds"] == len(ids) * 0.125
    )
    bad = [dict(g, type="FORBIDDEN") if g["id"] in ids else g for g in gold]
    (source / "answers.jsonl").write_text(
        "".join(json.dumps(g) + "\n" for g in bad), encoding="utf-8"
    )
    with pytest.raises(ValueError):
        read_scoped(split, digest, "dev", "gold", "evaluation", "evaluator", H)
    last = read_ledger(split / "access.jsonl")[-1]
    assert last["kind"] == "scoped_read_failed" and last["decode_attempts"] == 1
    assert last["gold_content_read"] and "answer" not in last


def test_invalid_bootstrap_parameters_fail_before_gold(
    scoped_fixture, tmp_path, monkeypatch
):
    _, split, digest, _, _ = scoped_fixture
    empty = tmp_path / "empty.jsonl"
    empty.write_bytes(b"")
    original = Path.open

    def no_gold(path, *args, **kwargs):
        if path.name == "answers.jsonl":
            raise AssertionError("Bad statistical config must fail before gold")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", no_gold)
    with pytest.raises(ValueError):
        run_eval(
            split,
            digest,
            "dev",
            empty,
            tmp_path / "bad-stats",
            ROOT / "configs/scoring_policy.json",
            control=empty,
            replicates=999,
        )


@pytest.mark.parametrize(
    "argument", ["submission", "policy_path", "taxonomy", "execution", "rules"]
)
def test_gold_cannot_be_smuggled_as_unscoped_external_input(
    scoped_fixture, tmp_path, monkeypatch, argument
):
    source, split, digest, _, _ = scoped_fixture
    empty = tmp_path / "empty.jsonl"
    empty.write_bytes(b"")
    gold = source / "answers.jsonl"
    original = Path.open

    def no_gold(path, *args, **kwargs):
        if path.name == "answers.jsonl":
            raise AssertionError("Raw gold bypass attempted")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", no_gold)
    with pytest.raises(ValueError, match="external"):
        if argument == "rules":
            run_taxonomy(split, digest, gold, tmp_path / "bad-rules")
        else:
            args = dict(
                split=split,
                manifest_sha256=digest,
                partition="dev",
                submission=empty,
                output=tmp_path / "bad-external",
                policy_path=ROOT / "configs/scoring_policy.json",
            )
            args[argument] = gold
            run_eval(**args)
