import json
import shutil
from pathlib import Path

import pytest

from datamate.cli import main
from datamate.runner import read_questions, run_stub
from datamate.validation import inspect_input, inspect_logs, inspect_submission

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def split(tmp_path):
    path = tmp_path / "split"
    shutil.copytree(ROOT / "tests/fixtures/synthetic", path)
    business = path / "data" / "synthetic"
    business.mkdir(parents=True)
    (business / "README.md").write_text("Synthetic contract business")
    shutil.copyfile(path / "sales.csv", business / "sales.csv")
    (path / "answers.jsonl").write_text("gold must never be parsed")
    return path


def test_input_audit_checks_references_and_never_opens_gold(split, monkeypatch):
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        assert path.name != "answers.jsonl", "Validation must not open gold labels"
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    report = inspect_input(split)
    assert report["valid"]
    assert report["questions"] == 2
    assert report["referenced_businesses"] == 1
    assert report["gold_file_present"] and not report["gold_content_read"]
    assert set(report["input_sha256"]) == {
        "questions.jsonl",
        "rulebook.md",
        "calendar.csv",
    }


@pytest.mark.parametrize(
    "fault", ["missing_rulebook", "missing_business", "path_traversal", "missing_table"]
)
def test_bad_split_fails_with_explicit_contract_error(split, fault):
    if fault == "missing_rulebook":
        (split / "rulebook.md").unlink()
    elif fault == "missing_business":
        (split / "data" / "synthetic").rename(split / "data" / "renamed")
    elif fault == "missing_table":
        (split / "data" / "synthetic" / "sales.csv").unlink()
    else:
        path = split / "questions.jsonl"
        path.write_text(path.read_text().replace('"synthetic"', '"../outside"'))
    result = inspect_input(split)
    assert not result["valid"] and result["errors"]


def test_missing_predictions_are_abstain_but_complete_run_policy_detects_them(
    split, tmp_path
):
    empty = tmp_path / "submission.jsonl"
    empty.write_text("")
    allowed = inspect_submission(split, empty)
    assert allowed["valid"] and allowed["missing_ids_counted_as_abstain"] == 2
    required = inspect_submission(split, empty, require_complete=True)
    assert not required["valid"]
    assert required["pa"] == "not_evaluated"


@pytest.mark.parametrize(
    "fault", ["duplicate", "unknown", "boolean_as_number", "duplicate_json_key", "nan"]
)
def test_bad_predictions_do_not_silently_overwrite_or_coerce(split, tmp_path, fault):
    records = [{"id": "synthetic_sum", "type": "abstain"}]
    if fault == "duplicate":
        records *= 2
    elif fault == "unknown":
        records[0]["id"] = "not_in_input"
    elif fault == "boolean_as_number":
        records[0].update(type="number", answer=True)
    path = tmp_path / "submission.jsonl"
    if fault == "duplicate_json_key":
        path.write_text('{"id":"a","id":"synthetic_sum","type":"abstain"}\n')
    elif fault == "nan":
        path.write_text('{"id":"synthetic_sum","type":"number","answer":NaN}\n')
    else:
        path.write_text("".join(json.dumps(item) + "\n" for item in records))
    result = inspect_submission(split, path)
    assert not result["valid"] and result["errors"]


def test_log_matches_submission_and_missing_log_fails(split, tmp_path):
    run = run_stub(split, tmp_path / "run")
    assert inspect_logs(split, run)["valid"]
    first = run / "logs" / "000000.json"
    log = json.loads(first.read_text())
    log["answer"] = {"id": "synthetic_sum", "type": "string", "answer": "different"}
    first.write_text(json.dumps(log))
    assert not inspect_logs(split, run)["valid"]
    first.unlink()
    assert not inspect_logs(split, run)["valid"]


def test_cli_validation_failure_has_nonzero_exit(split, monkeypatch, capsys):
    (split / "rulebook.md").unlink()
    monkeypatch.setattr(
        "sys.argv", ["datamate", "validate-input", "--input", str(split)]
    )
    assert main() == 2
    assert not json.loads(capsys.readouterr().out)["valid"]


def test_duplicate_json_field_in_question_is_rejected(split):
    path = split / "questions.jsonl"
    path.write_text(
        '{"id":"q","id":"other","business_id":"synthetic",'
        '"question":"synthetic?","as_of_date":"2026-03-04"}\n'
    )
    with pytest.raises(ValueError, match="duplicate JSON key"):
        read_questions(path)
