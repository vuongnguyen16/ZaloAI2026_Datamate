import json
import os
import subprocess
import sys
import time

import pytest

from datamate.prediction import read_prediction_questions, run_predict
from datamate.scoring import parse_object


def question(qid):
    return dict(
        id=qid, business_id="fixture", question="Synthetic?", as_of_date="2026-11-06"
    )


def inputs(tmp_path, count=3):
    root = tmp_path / "input"
    root.mkdir()
    (root / "questions.jsonl").write_text(
        "".join(json.dumps(question(str(i))) + "\n" for i in range(count)),
        encoding="utf-8",
    )
    (root / "answers.jsonl").write_bytes(b"GOLD SENTINEL - NEVER PARSE")
    return root


def results(output):
    return [
        parse_object(line)
        for line in (output / "submission.jsonl").read_bytes().splitlines()
    ]


def sleeping_backend(question):
    time.sleep(30)


def test_worker_start_failure_and_timeout_are_abstain(tmp_path):
    root = inputs(tmp_path)
    startup = tmp_path / "startup"
    run_predict(root, startup, backend=lambda q: None)
    assert all(p["type"] == "abstain" for p in results(startup))
    timed = tmp_path / "timed"
    run_predict(root, timed, {"per_question_seconds": 0.2}, backend=sleeping_backend)
    assert results(timed)[0]["reason"] == "backend_timeout"
    # A question-local timeout no longer poisons the remaining backend calls.
    assert results(timed)[-1]["reason"] == "backend_timeout"


def test_bad_line_and_duplicate_do_not_lose_remaining_ids(tmp_path):
    root = inputs(tmp_path)
    with (root / "questions.jsonl").open("a", encoding="utf-8") as out:
        out.write('broken {"id":"do-not-guess"\n')
        out.write(json.dumps(question("0")) + "\n")
        out.write(json.dumps({**question("1"), "question": "Conflicting"}) + "\n")
        out.write('{"id":"invalid","question":3}\n')
    questions, rejected, errors = read_prediction_questions(root / "questions.jsonl")
    assert set(questions) == {"0", "2"}
    assert set(rejected) == {"1", "invalid"}
    assert errors
    output = tmp_path / "out"
    original = (root / "questions.jsonl").read_bytes()
    result = run_predict(root, output)
    assert result["valid"] and result["data_error_count"] >= 2
    assert {p["id"] for p in results(output)} == {"0", "1", "2", "invalid"}
    assert (root / "questions.jsonl").read_bytes() == original
    assert (root / "answers.jsonl").read_bytes() == b"GOLD SENTINEL - NEVER PARSE"


def test_resume_and_input_config_mismatch_preserve_final(tmp_path):
    root = inputs(tmp_path)
    output = tmp_path / "out"
    run_predict(root, output)
    final = (output / "submission.jsonl").read_bytes()
    assert run_predict(root, output)["publication"]["status"] == "reused"
    assert len(results(output)) == 3
    with pytest.raises(ValueError, match="identity"):
        run_predict(root, output, {"budget_seconds": 100, "reserve_seconds": 1})
    (root / "questions.jsonl").write_text(json.dumps(question("new")) + "\n")
    with pytest.raises(ValueError, match="identity"):
        run_predict(root, output)
    assert (output / "submission.jsonl").read_bytes() == final


def test_backend_failure_and_expired_startup_finalize_all(tmp_path):
    root = inputs(tmp_path)
    output = tmp_path / "out"
    # int(dict) raises inside the spawned worker; fixture only, never a real model.
    result = run_predict(root, output, backend=int)
    assert result["valid"]
    assert all(p["type"] == "abstain" for p in results(output))
    assert results(output)[0]["reason"] == "backend_error"
    expired = tmp_path / "expired"
    run_predict(
        root,
        expired,
        {"budget_seconds": 5, "reserve_seconds": 1},
        started=time.monotonic() - 10,
    )
    assert all(p["reason"] == "deadline" for p in results(expired))


def test_existing_final_conflict_and_foreign_output(tmp_path):
    root = inputs(tmp_path)
    output = tmp_path / "out"
    run_predict(root, output)
    (output / "submission.jsonl").write_bytes(b"preserve")
    with pytest.raises(FileExistsError):
        run_predict(root, output)
    assert (output / "submission.jsonl").read_bytes() == b"preserve"
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "user.txt").write_text("mine")
    with pytest.raises(ValueError, match="foreign"):
        run_predict(root, foreign)


def test_cli_and_real_process_kill_resume(tmp_path):
    root = inputs(tmp_path, 2000)
    output = tmp_path / "out"
    command = [
        sys.executable,
        "-m",
        "datamate.cli",
        "predict",
        "--input",
        str(root),
        "--output",
        str(output),
    ]
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    with (tmp_path / "child.log").open("wb") as log:
        child = subprocess.Popen(command, stdout=log, stderr=log, env=env)
        try:
            deadline = time.monotonic() + 15
            checkpoint_seen = False
            while time.monotonic() < deadline and child.poll() is None:
                if any(
                    p.stat().st_size > 100
                    for p in (output / "logs/.state").glob("segment-*.jsonl")
                ):
                    checkpoint_seen = True
                    child.kill()
                    break
                time.sleep(0.01)
            assert checkpoint_seen, (tmp_path / "child.log").read_text()
        finally:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
    resumed = subprocess.run(command, capture_output=True, timeout=35, env=env)
    assert resumed.returncode == 0, resumed.stderr
    assert len(results(output)) == 2000
    assert len({p["id"] for p in results(output)}) == 2000
    assert json.loads(resumed.stdout)["backend"] == "no_model"


def test_invalid_numeric_values_are_contained_and_known_ids_accounted(tmp_path):
    root = inputs(tmp_path, 1)
    with (root / "questions.jsonl").open("ab") as handle:
        handle.write(b'{"id":"bad","question":1e9999999999999999999999999}\n')
    run_predict(root, tmp_path / "mixed")
    assert {p["id"] for p in results(tmp_path / "mixed")} == {"0", "bad"}
    (root / "questions.jsonl").write_bytes(b'{"id":"bad","question":1e1001}\n')
    run_predict(root, tmp_path / "only-bad")
    assert results(tmp_path / "only-bad")[0]["type"] == "abstain"


def test_rejected_ids_count_toward_limit_and_reordered_duplicates_deduplicate(tmp_path):
    root = inputs(tmp_path, 1)
    with (root / "questions.jsonl").open("a") as handle:
        handle.write(json.dumps(dict(reversed(list(question("0").items())))) + "\n")
    accepted, rejected, _ = read_prediction_questions(root / "questions.jsonl")
    assert set(accepted) == {"0"} and not rejected
    (root / "questions.jsonl").write_bytes(
        b"".join(b'{"id":"bad%d","question":1e1001}\n' % i for i in range(10001))
    )
    with pytest.raises(ValueError, match="count"):
        read_prediction_questions(root / "questions.jsonl")


def large_backend(question):
    return {"type": "string", "answer": "x" * 500}


def test_aggregate_output_budget_abstains_and_streams_final(tmp_path, monkeypatch):
    import datamate.prediction as module

    root = inputs(tmp_path, 5)
    monkeypatch.setattr(module, "MAX_OUTPUT_BYTES", 800, raising=False)
    result = run_predict(root, tmp_path / "out", backend=large_backend)
    assert result["valid"]
    rows = results(tmp_path / "out")
    assert len(rows) == 5 and any(p.get("reason") == "output_budget" for p in rows)
    assert (tmp_path / "out/submission.jsonl").stat().st_size <= 800


def test_effective_default_reserve_matches_shipped_six_hour_config():
    from pathlib import Path

    import yaml

    from datamate.prediction import DEFAULTS

    config = yaml.safe_load(
        (Path(__file__).resolve().parents[2] / "configs/predict.yaml").read_text(
            "utf-8"
        )
    )
    assert DEFAULTS == config
