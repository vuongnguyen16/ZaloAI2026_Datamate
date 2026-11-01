import json
import shutil
from pathlib import Path

import pytest
import yaml

from datamate.artifacts import sha256
from datamate.runner import read_questions, run_smoke, run_stub

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def fixture_config(tmp_path):
    inputs = tmp_path / "fixture"
    shutil.copytree(ROOT / "tests/fixtures/synthetic", inputs)
    config = yaml.safe_load((ROOT / "configs/smoke.yaml").read_text("utf-8"))
    config.update(input_dir="fixture", output_root="output")
    path = tmp_path / "smoke.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path, inputs


def records(path):
    return [json.loads(line) for line in path.read_text("utf-8").splitlines()]


@pytest.mark.integration
def test_decimal_sum_code_provenance_and_no_input_mutation(fixture_config):
    config, inputs = fixture_config
    before = {p.name: sha256(p) for p in inputs.iterdir()}
    first = run_smoke(config)
    second = run_smoke(config)
    expected = [
        {"id": "synthetic_sum", "type": "number", "answer": 12.35},
        {"id": "synthetic_code", "type": "string", "answer": "0012"},
    ]
    assert records(first / "submission.jsonl") == expected
    assert records(second / "submission.jsonl") == expected
    assert first != second
    assert json.loads((first / "manifest.json").read_text())["input_files_sha256"]
    assert json.loads((first / "summary.json").read_text())["pa"] == "not_evaluated"
    assert {p.name: sha256(p) for p in inputs.iterdir()} == before


@pytest.mark.integration
@pytest.mark.parametrize("failure", ["malformed", "bad_sql"])
def test_failed_response_abstains_and_next_question_survives(fixture_config, failure):
    config, inputs = fixture_config
    path = inputs / "responses.json"
    responses = json.loads(path.read_text())
    responses[0] = (
        {"unexpected": "bad response"}
        if failure == "malformed"
        else {
            "sql": "SELECT unknown_column FROM sales",
            "answer_type": "number",
        }
    )
    path.write_text(json.dumps(responses))
    run = run_smoke(config)
    output = records(run / "submission.jsonl")
    assert output[0] == {"id": "synthetic_sum", "type": "abstain"}
    assert output[1]["answer"] == "0012"
    events = records(run / "events.jsonl")
    assert events[0]["status"] == "error"
    assert events[1]["status"] == "ok"


@pytest.mark.parametrize("failure", ["duplicate", "missing_id"])
def test_invalid_ids_rejected_before_run(fixture_config, failure):
    config, inputs = fixture_config
    path = inputs / "questions.jsonl"
    questions = records(path)
    if failure == "duplicate":
        questions[1]["id"] = questions[0]["id"]
    else:
        del questions[0]["id"]
    path.write_text("".join(json.dumps(q) + "\n" for q in questions))
    with pytest.raises(ValueError, match="duplicate|invalid question"):
        run_smoke(config)
    assert not (config.parent / "output").exists()


@pytest.mark.parametrize("failure", ["unknown_key", "oversize", "missing_file"])
def test_config_and_local_budgets_fail_closed(fixture_config, failure):
    config, inputs = fixture_config
    settings = yaml.safe_load(config.read_text())
    if failure == "unknown_key":
        settings["adapetr"] = "real"
    elif failure == "oversize":
        settings["max_fixture_bytes"] = 1
    else:
        (inputs / "sales.csv").unlink()
    config.write_text(yaml.safe_dump(settings))
    with pytest.raises(ValueError):
        run_smoke(config)


def test_stub_never_reads_gold_and_logs_every_question(fixture_config, tmp_path):
    _, inputs = fixture_config
    # Gold cannot even be parsed. The stub has no need to read it.
    (inputs / "answers.jsonl").write_text("THIS IS NOT JSON")
    run = run_stub(inputs, tmp_path / "stub")
    assert records(run / "submission.jsonl") == [
        {"id": q.id, "type": "abstain"}
        for q in read_questions(inputs / "questions.jsonl")
    ]
    assert len(list((run / "logs").glob("*.json"))) == 2
    assert all("duration_seconds" in e for e in records(run / "events.jsonl"))
    with pytest.raises(ValueError, match="new or empty"):
        run_stub(inputs, run)
