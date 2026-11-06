import json
from pathlib import Path

import pytest

from datamate.prediction import run_predict
from datamate.prediction_failsafe import submission_predict
from tests.integration.test_prediction import inputs, results


def test_unmanaged_output_is_ignored_without_reading_or_stating_it(
    tmp_path, monkeypatch
):
    root = inputs(tmp_path)
    output = tmp_path / "result"
    unknown = output / "lost+found"
    unknown.mkdir(parents=True)
    (unknown / "keep").write_bytes(b"private-content")
    note = output / "user.txt"
    note.write_bytes(b"unchanged")
    original_stat, original_open = Path.stat, Path.open

    def guard_stat(path, *a, **k):
        assert path not in {unknown, note}, "unmanaged entry was inspected"
        return original_stat(path, *a, **k)

    def guard_open(path, *a, **k):
        assert path != note and unknown not in path.parents, (
            "unmanaged content was opened"
        )
        return original_open(path, *a, **k)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "stat", guard_stat)
        patch.setattr(Path, "open", guard_open)
        outcome = submission_predict(root, output)
    assert outcome["valid"] and outcome["backend"] == "no_model"
    assert len(results(output)) == 3
    assert note.read_bytes() == b"unchanged"
    assert (unknown / "keep").read_bytes() == b"private-content"
    diagnostic = json.loads(
        next((output / "logs/.state").glob("diagnostics-*.json")).read_text("utf-8")
    )
    assert diagnostic["ignored_output_entries"] == ["lost+found", "user.txt"]


def test_failsafe_also_reports_unmanaged_output_names(tmp_path):
    root = inputs(tmp_path)
    output = tmp_path / "result"
    (output / "lost+found").mkdir(parents=True)
    config = tmp_path / "invalid.yaml"
    config.write_text("[broken")
    outcome = submission_predict(root, output, config_path=config)
    assert outcome["valid"] and outcome["mode"] == "failsafe_all_abstain"
    assert outcome["ignored_output_entries"] == ["lost+found"]


@pytest.mark.parametrize("status", ["timeout", "error"])
def test_three_question_failures_do_not_disable_later_business(
    tmp_path, monkeypatch, status
):
    import datamate.prediction as module

    root = inputs(tmp_path, 5)
    output = tmp_path / "result"
    calls = []

    def response(backend, args, timeout):
        calls.append(args[0]["id"])
        if len(calls) <= 3:
            return {"status": status, "error": "query_failure"}
        return {"status": "ok", "value": {"type": "number", "answer": 7}}

    monkeypatch.setattr(module, "run_bounded", response)
    run_predict(root, output, backend=int)
    rows = results(output)
    assert calls == ["0", "1", "2", "3", "4"]
    assert all(r["reason"] == "backend_" + status for r in rows[:3])
    assert [r["answer"] for r in rows[3:]] == [7, 7]


@pytest.mark.parametrize(
    "failure",
    [
        {"status": "startup_error"},
        {"status": "error", "error": "worker_exited"},
        {"status": "error", "error": "invalid_worker_result"},
    ],
)
def test_proven_backend_failure_still_disables_backend(tmp_path, monkeypatch, failure):
    import datamate.prediction as module

    calls = []

    def response(*args):
        calls.append(1)
        return failure

    monkeypatch.setattr(module, "run_bounded", response)
    root = inputs(tmp_path)
    output = tmp_path / "result"
    run_predict(root, output, backend=int)
    assert len(calls) == 1
    assert all(r["reason"] == "backend_unavailable" for r in results(output)[1:])


@pytest.mark.parametrize("owned", ["logs", "submission.jsonl"])
def test_owned_output_path_type_conflicts_are_still_refused(tmp_path, owned):
    root = inputs(tmp_path)
    output = tmp_path / "result"
    output.mkdir()
    if owned == "logs":
        (output / owned).write_bytes(b"existing-file")
    else:
        (output / owned).mkdir()
    assert not submission_predict(root, output)["valid"]
    if owned == "logs":
        assert (output / owned).read_bytes() == b"existing-file"
