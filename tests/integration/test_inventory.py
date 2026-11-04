"""Synthetic integration tests for the mechanical data inventory tool."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.inventory import (  # noqa: E402
    build_inventory,
    main,
    run_inventory,
)


@pytest.fixture
def two_business_split(tmp_path: Path) -> Path:
    """Create a minimal synthetic split with 2 businesses and valid files."""
    split = tmp_path / "split_two_biz"
    split.mkdir()

    # questions.jsonl
    q_lines = [
        {
            "id": "q1",
            "business_id": "biz_alpha",
            "question": "Do not output",
            "as_of_date": "2025-01-01",
        },
        {
            "id": "q2",
            "business_id": "biz_alpha",
            "question": "Secret prompt text",
            "as_of_date": "2025-01-02",
        },
        {
            "id": "q3",
            "business_id": "biz_beta",
            "question": "Confidential text",
            "as_of_date": "2025-01-03",
        },
        {
            "id": "q4",
            "business_id": "biz_beta",
            "question": "Private value",
            "as_of_date": "2025-01-04",
        },
        {
            "id": "q5",
            "business_id": "biz_beta",
            "question": "Gold answer inquiry",
            "as_of_date": "2025-01-05",
        },
    ]
    (split / "questions.jsonl").write_text(
        "".join(json.dumps(q) + "\n" for q in q_lines),
        encoding="utf-8",
    )

    # biz_alpha
    biz_a = split / "data" / "biz_alpha"
    biz_a.mkdir(parents=True)
    (biz_a / "README.md").write_text("Context for alpha", encoding="utf-8")
    (biz_a / "sales.csv").write_text("col_a,col_b\n1,2\n", encoding="utf-8")

    # biz_beta
    biz_b = split / "data" / "biz_beta"
    biz_b.mkdir(parents=True)
    (biz_b / "README.md").write_text("Context for beta", encoding="utf-8")
    (biz_b / "inventory.sqlite").write_bytes(b"SQLite format 3\x00synthetic_db_header")

    return split


def test_two_business_counting_and_no_question_text_leak(
    two_business_split: Path, tmp_path: Path
):
    """Test accurate mechanical counting across two businesses without text leakage."""
    out_dir = tmp_path / "runs" / "test-inv-two-biz"
    report = run_inventory(two_business_split, out_dir)

    assert (out_dir / "inventory.json").is_file()
    assert (out_dir / "inventory.md").is_file()

    summary = report["summary"]
    assert summary["total_businesses"] == 2
    assert summary["total_questions"] == 5
    assert (
        summary["total_files"] == 5
    )  # 2 files in biz_a + 2 files in biz_b + 1 questions.jsonl
    assert summary["business_files"] == 4
    assert summary["top_level_files"] == 1
    assert summary["identical_table_groups"] == 0
    assert summary["error_count"] == 0

    businesses = {b["business_id"]: b for b in report["businesses"]}
    assert set(businesses.keys()) == {"biz_alpha", "biz_beta"}

    alpha = businesses["biz_alpha"]
    assert alpha["question_count"] == 2
    assert alpha["file_count"] == 2
    assert alpha["extension_distribution"] == {".csv": 1, ".md": 1}

    beta = businesses["biz_beta"]
    assert beta["question_count"] == 3
    assert beta["file_count"] == 2
    assert beta["extension_distribution"] == {".md": 1, ".sqlite": 1}

    # Verify that neither question text nor sensitive tokens appear in output
    raw_json = (out_dir / "inventory.json").read_text(encoding="utf-8")
    raw_md = (out_dir / "inventory.md").read_text(encoding="utf-8")
    for forbidden in (
        "Do not output",
        "Secret prompt text",
        "Confidential text",
        "Private value",
        "Gold answer inquiry",
    ):
        assert forbidden not in raw_json
        assert forbidden not in raw_md


def test_detects_identical_table_files_across_businesses(tmp_path: Path):
    """Test detection and grouping of byte-identical table files with different names."""
    split = tmp_path / "split_dupe_tables"
    split.mkdir()

    (split / "questions.jsonl").write_text(
        json.dumps(
            {
                "id": "q1",
                "business_id": "biz_1",
                "question": "test",
                "as_of_date": "2025-01-01",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    biz_1 = split / "data" / "biz_1"
    biz_1.mkdir(parents=True)
    biz_2 = split / "data" / "biz_2"
    biz_2.mkdir(parents=True)

    identical_content = b"header_1,header_2\nval_a,val_b\nval_c,val_d\n"

    # Different filenames, identical bytes
    (biz_1 / "bang_gia_goc.csv").write_bytes(identical_content)
    (biz_2 / "price_list_copy.csv").write_bytes(identical_content)

    # Distinct file in biz_1
    (biz_1 / "other.csv").write_bytes(b"distinct,table\n1,2\n")

    report = build_inventory(split)

    assert len(report["identical_table_files"]) == 1
    group = report["identical_table_files"][0]
    assert group["file_count"] == 2
    assert group["businesses"] == ["biz_1", "biz_2"]
    assert group["files"] == [
        "data/biz_1/bang_gia_goc.csv",
        "data/biz_2/price_list_copy.csv",
    ]
    assert "observation_note" in group
    assert "không tự kết luận" in group["observation_note"]


def test_detects_duplicate_question_id_and_faulty_business_reference(tmp_path: Path):
    """Test structured error detection: duplicate IDs, missing references, and bad JSONL."""
    split = tmp_path / "split_faulty"
    split.mkdir()

    biz_valid = split / "data" / "biz_valid"
    biz_valid.mkdir(parents=True)
    (biz_valid / "table.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    lines = [
        # Line 1: valid
        json.dumps({"id": "dup_01", "business_id": "biz_valid"}),
        # Line 2: duplicate question ID
        json.dumps({"id": "dup_01", "business_id": "biz_valid"}),
        # Line 3: non-existent business reference
        json.dumps({"id": "q_bad_biz", "business_id": "biz_nonexistent"}),
        # Line 4: missing id field
        json.dumps({"business_id": "biz_valid"}),
        # Line 5: missing business_id field
        json.dumps({"id": "q_missing_biz"}),
        # Line 6: invalid business reference characters (path traversal attempt)
        json.dumps({"id": "q_traversal", "business_id": "../escaping"}),
        # Line 7: malformed JSON syntax
        "{not valid json: true, broken",
        # Line 8: not an object
        json.dumps(["a", "list", "instead", "of", "dict"]),
    ]
    (split / "questions.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    report = build_inventory(split)
    errors = report["errors"]
    error_types = [e["type"] for e in errors]

    assert "duplicate_question_id" in error_types
    assert "nonexistent_business" in error_types
    assert "missing_id" in error_types
    assert "missing_business_id" in error_types
    assert "invalid_business_reference" in error_types
    assert "malformed_jsonl" in error_types
    assert "not_an_object" in error_types

    # Verify duplicate question details
    dup_err = next(e for e in errors if e["type"] == "duplicate_question_id")
    assert dup_err["question_id"] == "dup_01"
    assert dup_err["line"] == 2
    assert dup_err["first_seen_line"] == 1

    # Verify non-existent business details
    nonexist_err = next(e for e in errors if e["type"] == "nonexistent_business")
    assert nonexist_err["question_id"] == "q_bad_biz"
    assert nonexist_err["business_id"] == "biz_nonexistent"
    assert nonexist_err["line"] == 3


def test_gold_answers_with_malformed_json_never_parsed(tmp_path: Path):
    """Test that answers.jsonl containing invalid JSON is never parsed as JSON."""
    split = tmp_path / "split_gold_malformed"
    split.mkdir()

    (split / "questions.jsonl").write_text(
        json.dumps({"id": "q1", "business_id": "biz_single"}) + "\n",
        encoding="utf-8",
    )
    biz = split / "data" / "biz_single"
    biz.mkdir(parents=True)
    (biz / "data.csv").write_text("x,y\n1,2\n", encoding="utf-8")

    # answers.jsonl with completely malformed JSON syntax
    (split / "answers.jsonl").write_text(
        "MALFORMED GOLD JSON: {{{ not json, answer: undefined, NaN\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "out_gold_test"
    report = run_inventory(split, out_dir)

    # Must complete cleanly without crashing on malformed answers.jsonl
    assert report["summary"]["error_count"] == 0
    assert any(f["path"] == "answers.jsonl" for f in report["files"])

    # Verify answers.jsonl hash is recorded as a raw binary file
    gold_file_rec = next(f for f in report["files"] if f["path"] == "answers.jsonl")
    assert gold_file_rec["size_bytes"] > 0
    assert len(gold_file_rec["sha256"]) == 64


def test_refuses_to_overwrite_existing_output_directory(
    two_business_split: Path, tmp_path: Path
):
    """Test that run_inventory and CLI fail when output directory already exists."""
    out_dir = tmp_path / "existing_output"
    out_dir.mkdir()
    sentinel = out_dir / "sentinel.txt"
    sentinel.write_text("do not overwrite", encoding="utf-8")

    # Python function API check
    with pytest.raises(FileExistsError):
        run_inventory(two_business_split, out_dir)
    assert sentinel.read_text(encoding="utf-8") == "do not overwrite"

    # CLI invocation check
    exit_code = main(["--input", str(two_business_split), "--output", str(out_dir)])
    assert exit_code == 1
    assert sentinel.read_text(encoding="utf-8") == "do not overwrite"


@pytest.mark.parametrize("relative_output", [".", "new/output"])
def test_output_inside_input_is_rejected_before_any_write(
    two_business_split: Path, relative_output: str
):
    before = {p.relative_to(two_business_split) for p in two_business_split.rglob("*")}
    output = two_business_split / relative_output
    with pytest.raises(ValueError, match="outside input"):
        run_inventory(two_business_split, output)
    assert main(["--input", str(two_business_split), "--output", str(output)]) != 0
    assert {
        p.relative_to(two_business_split) for p in two_business_split.rglob("*")
    } == before


def test_output_alias_into_input_is_rejected(two_business_split: Path, tmp_path: Path):
    alias = tmp_path / "input_alias"
    if os.name == "nt":
        # Junction creation needs no symlink privilege on Windows.
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(alias), str(two_business_split)],
            check=True,
            capture_output=True,
        )
    else:
        alias.symlink_to(two_business_split, target_is_directory=True)
    output = alias / "new" / "output"
    with pytest.raises(ValueError, match="outside input"):
        run_inventory(two_business_split, output)
    assert not (two_business_split / "new").exists()


def test_question_counts_exclude_invalid_and_all_duplicate_ids(
    two_business_split: Path, tmp_path: Path
):
    records = [
        {"id": "ok", "business_id": "biz_alpha"},
        {"id": "dup", "business_id": "biz_alpha"},
        {"id": "dup", "business_id": "biz_beta"},
        {"id": "missing_business"},
        {"id": "unknown_business", "business_id": "does_not_exist"},
        {"business_id": "biz_beta"},
        {"id": "bad_business_path", "business_id": "../outside"},
    ]
    questions = two_business_split / "questions.jsonl"
    questions.write_text(
        "".join(json.dumps(q) + "\n" for q in records), encoding="utf-8"
    )
    report = build_inventory(two_business_split)
    summary = report["summary"]
    assert summary["question_lines"] == 7
    assert summary["unique_question_ids"] == 5
    assert summary["duplicate_question_ids"] == 1
    assert summary["total_questions"] == 1
    assert sum(b["question_count"] for b in report["businesses"]) == 1
    assert {b["business_id"]: b["question_count"] for b in report["businesses"]} == {
        "biz_alpha": 1,
        "biz_beta": 0,
    }
    questions.write_text(
        "".join(json.dumps(q) + "\n" for q in reversed(records)), encoding="utf-8"
    )
    reversed_report = build_inventory(two_business_split)
    assert reversed_report["summary"] == summary
    assert reversed_report["businesses"] == report["businesses"]

    output = tmp_path / "invalid-report"
    assert main(["--input", str(two_business_split), "--output", str(output)]) != 0
    saved = json.loads((output / "inventory.json").read_text("utf-8"))
    assert saved["errors"]
    assert saved["summary"]["total_questions"] == 1
    assert (output / "inventory.md").is_file()


def test_identifiers_are_not_trimmed(two_business_split: Path):
    records = [
        {"id": "q", "business_id": "biz_alpha"},
        {"id": " q ", "business_id": "biz_beta"},
        {"id": "wrong_ref", "business_id": " biz_alpha "},
    ]
    (two_business_split / "questions.jsonl").write_text(
        "".join(json.dumps(q) + "\n" for q in records), encoding="utf-8"
    )
    report = build_inventory(two_business_split)
    assert report["summary"]["unique_question_ids"] == 3
    assert report["summary"]["total_questions"] == 2
    assert report["summary"]["duplicate_question_ids"] == 0
    assert [e["type"] for e in report["errors"]] == ["nonexistent_business"]
    assert report["errors"][0]["business_id"] == " biz_alpha "


@pytest.mark.parametrize(
    "invalid_json",
    [
        '{"id":"q","business_id":"biz_alpha","question":NaN}',
        '{"id":"q","business_id":"biz_alpha","question":Infinity}',
        '{"id":"q","business_id":"biz_alpha","question":-Infinity}',
        '{"id":"q","id":"q2","business_id":"biz_alpha"}',
        '{"id":"q","business_id":"biz_alpha",'
        '"question":{"DO_NOT_LEAK_KEY":1,"DO_NOT_LEAK_KEY":2}}',
    ],
)
def test_strict_json_errors_do_not_leak_content(
    two_business_split: Path, tmp_path: Path, invalid_json: str
):
    (two_business_split / "questions.jsonl").write_text(
        invalid_json + "\n", encoding="utf-8"
    )
    output = tmp_path / "strict-json-report"
    assert main(["--input", str(two_business_split), "--output", str(output)]) != 0
    report = json.loads((output / "inventory.json").read_text("utf-8"))
    assert [e["type"] for e in report["errors"]] == ["malformed_jsonl"]
    assert report["summary"]["total_questions"] == 0
    for name in ("inventory.json", "inventory.md"):
        assert "DO_NOT_LEAK_KEY" not in (output / name).read_text("utf-8")


def test_invalid_id_object_is_not_echoed_in_errors(two_business_split: Path):
    (two_business_split / "questions.jsonl").write_text(
        json.dumps({"id": {"private": "DO_NOT_LEAK_VALUE"}, "business_id": "missing"})
        + "\n",
        encoding="utf-8",
    )
    report = build_inventory(two_business_split)
    assert report["summary"]["total_questions"] == 0
    assert "DO_NOT_LEAK_VALUE" not in json.dumps(report)


def test_valid_inventory_cli_succeeds(two_business_split: Path, tmp_path: Path):
    assert (
        main(
            [
                "--input",
                str(two_business_split),
                "--output",
                str(tmp_path / "valid-report"),
            ]
        )
        == 0
    )
