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
    assert results(timed)[-1]["reason"] == "backend_unavailable"


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
        run_predict(root, output, {"budget_seconds": 100})
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
                if any(p.stat().st_size > 100 for p in output.glob("segment-*.jsonl")):
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
