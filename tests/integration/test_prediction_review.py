import errno
import os
import time

import pytest

from datamate.prediction import run_predict
from datamate.validation import inspect_logs
from tests.integration.test_prediction import inputs, results


def one_slow_question(question):
    if question["id"] == "0":
        time.sleep(30)
    return {"type": "number", "answer": 7}


def test_preexisting_logs_directory_produces_contract_logs(tmp_path):
    root = inputs(tmp_path)
    output = tmp_path / "out"
    (output / "logs").mkdir(parents=True)
    outcome = run_predict(root, output)
    assert {p.name for p in output.iterdir()} == {"submission.jsonl", "logs"}
    assert (output / "logs/.state/identity.json").is_file()
    bound_logs = output / "logs" / f"submission-{outcome['publication']['sha256']}"
    assert len(list(bound_logs.glob("*.json"))) == 3
    assert inspect_logs(root, output)["valid"]


def test_one_actual_timeout_does_not_disable_following_questions(tmp_path):
    root = inputs(tmp_path, 4)
    output = tmp_path / "out"
    run_predict(root, output, {"per_question_seconds": 1.5}, backend=one_slow_question)
    rows = results(output)
    assert rows[0]["reason"] == "backend_timeout"
    assert [p["answer"] for p in rows[1:]] == [7, 7, 7]


def test_query_error_is_local_and_success_resets_consecutive_errors(
    tmp_path, monkeypatch
):
    import datamate.prediction as module

    def execute(backend, args, timeout):
        if args[0]["id"] in {"0", "2"}:
            return {"status": "error", "error": "query_error"}
        return {"status": "ok", "value": {"type": "number", "answer": 7}}

    monkeypatch.setattr(module, "run_bounded", execute)
    root = inputs(tmp_path, 4)
    run_predict(root, tmp_path / "out", backend=int)
    rows = results(tmp_path / "out")
    assert rows[0]["reason"] == rows[2]["reason"] == "backend_error"
    assert rows[1]["answer"] == rows[3]["answer"] == 7


def test_recursive_code_fingerprint_includes_relative_subpackage_paths(tmp_path):
    from datamate.prediction import code_fingerprint

    for directory in ("ingest", "profile"):
        (tmp_path / directory).mkdir()
        (tmp_path / directory / "same.py").write_text("value = 1\n")
    before = code_fingerprint(tmp_path)
    (tmp_path / "ingest/same.py").write_text("value = 2\n")
    after = code_fingerprint(tmp_path)
    assert before != after
    (tmp_path / "profile/same.py").write_text("value = 2\n")
    assert after != code_fingerprint(tmp_path)


@pytest.mark.parametrize("failure", ["startup", "inventory", "hardlink", "identity"])
def test_submission_entrypoint_falls_back_without_gold_or_checkpoint_reuse(
    tmp_path, monkeypatch, failure
):
    import datamate.prediction as module
    from datamate.prediction_failsafe import submission_predict

    root = inputs(tmp_path)
    output = tmp_path / "out"
    if failure == "identity":
        run_predict(root, output)
        (output / "submission.jsonl").unlink()
        old_manifest = (output / "logs/.state/identity.json").read_bytes()
        config = tmp_path / "config.yaml"
        config.write_text("budget_seconds: 100\nreserve_seconds: 1\n")
    else:
        config = None
        if failure == "startup":

            def broken(*a, **k):
                raise ImportError("synthetic startup")

            monkeypatch.setattr(module, "run_predict", broken)
        elif failure == "inventory":

            def huge(*a):
                raise ValueError("input byte inventory exceeds budget")

            monkeypatch.setattr(module, "_inventory", huge)
        else:
            os.link(root / "questions.jsonl", root / "questions-alias")
    outcome = submission_predict(root, output, config_path=config)
    assert outcome["valid"] and outcome["mode"] == "failsafe_all_abstain"
    assert len(results(output)) == 3
    assert all(
        p["type"] == "abstain" and p["reason"] == "runtime_fallback"
        for p in results(output)
    )
    assert (root / "answers.jsonl").read_bytes() == b"GOLD SENTINEL - NEVER PARSE"
    if failure == "identity":
        assert (output / "logs/.state/identity.json").read_bytes() == old_manifest


def test_failsafe_streams_more_than_dev_id_limit_and_deduplicates(
    tmp_path, monkeypatch
):
    import datamate.prediction_failsafe as module
    from datamate.prediction_failsafe import submission_predict

    # Exercise all 10001 real final lines/SQLite IDs; small tests cover physical
    # per-question fsync. Avoid 10001 redundant file flushes in this limit test.
    original = module.publish
    logged = []

    def log_sink(path, raw, **kwargs):
        if path.stem.isdigit():
            logged.append(path.name)
            return {"status": "synthetic_log_sink"}
        return original(path, raw, **kwargs)

    monkeypatch.setattr(module, "publish", log_sink)
    root = inputs(tmp_path, 10001)
    with (root / "questions.jsonl").open("ab") as handle:
        handle.write(b'{"id":"0"}\nmalformed {"id":"do-not-guess"\n')
    outcome = submission_predict(root, tmp_path / "out")
    assert outcome["valid"] and outcome["question_ids"] == 10001
    assert len(results(tmp_path / "out")) == 10001
    assert len(logged) == 10001
    assert {p["id"] for p in results(tmp_path / "out")} == {
        str(i) for i in range(10001)
    }


def test_failsafe_never_overwrites_existing_final_or_writes_into_input(
    tmp_path, monkeypatch
):
    from datamate.prediction_failsafe import submission_predict

    root = inputs(tmp_path)
    output = tmp_path / "out"
    output.mkdir()
    (output / "submission.jsonl").write_bytes(b"existing")
    config = tmp_path / "bad.yaml"
    config.write_text("[broken")
    assert not submission_predict(root, output, config_path=config)["valid"]
    assert (output / "submission.jsonl").read_bytes() == b"existing"
    assert not submission_predict(root, root, config_path=config)["valid"]
    assert not (root / "submission.jsonl").exists()


def test_submission_entrypoint_handles_unsupported_link_mount(tmp_path, monkeypatch):
    from datamate.prediction_failsafe import submission_predict

    def no_links(*args):
        raise OSError(errno.ENOTSUP, "synthetic mount")

    monkeypatch.setattr(os, "link", no_links)
    root = inputs(tmp_path)
    outcome = submission_predict(root, tmp_path / "out")
    assert outcome["valid"]
    assert outcome["publication"]["mode"] == "non_atomic_exclusive"
    assert len(results(tmp_path / "out")) == 3


def test_submission_fallback_accepts_aliased_input_ancestor(tmp_path):
    from datamate.prediction_failsafe import submission_predict

    root = inputs(tmp_path)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(root, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"host does not permit directory symlinks: {exc}")
    outcome = submission_predict(alias, tmp_path / "out")
    assert outcome["valid"] and outcome["mode"] == "failsafe_all_abstain"
    assert len(results(tmp_path / "out")) == 3


def test_actual_cli_config_error_uses_failsafe(tmp_path):
    import subprocess
    import sys

    root = inputs(tmp_path)
    config = tmp_path / "broken.yaml"
    config.write_text("[broken")
    output = tmp_path / "out"
    child = subprocess.run(
        [
            sys.executable,
            "-m",
            "datamate.cli",
            "predict",
            "--input",
            str(root),
            "--output",
            str(output),
            "--config",
            str(config),
        ],
        capture_output=True,
        timeout=20,
    )
    assert child.returncode == 0, child.stderr
    assert len(results(output)) == 3
    assert inspect_logs(root, output)["valid"]


@pytest.mark.parametrize("changed_config", [False, True])
def test_failsafe_cannot_steal_publication_from_active_writer(tmp_path, changed_config):
    import json
    import subprocess
    import sys

    from datamate.prediction_store import RunStore

    root = inputs(tmp_path)
    output = tmp_path / "out"
    run_predict(root, output)
    final = output / "submission.jsonl"
    final.unlink()
    state = output / "logs/.state"
    identity = json.loads((state / "identity.json").read_text("utf-8"))
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
    if changed_config:
        config = tmp_path / "different.yaml"
        config.write_text("budget_seconds: 100\nreserve_seconds: 1\n")
        command += ["--config", str(config)]
    with RunStore(state, identity):
        child = subprocess.run(command, capture_output=True, timeout=20)
        assert child.returncode != 0
        assert not final.exists(), "fallback stole the healthy writer's final path"


def test_submission_failsafe_retains_foreign_output_admission_guard(tmp_path):
    from datamate.prediction_failsafe import submission_predict

    root = inputs(tmp_path)
    output = tmp_path / "foreign"
    output.mkdir()
    (output / "user.txt").write_bytes(b"preserve")
    outcome = submission_predict(root, output)
    assert not outcome["valid"]
    assert not (output / "submission.jsonl").exists()
    assert (output / "user.txt").read_bytes() == b"preserve"


@pytest.mark.parametrize(
    "blocked", ["datamate.profile", "datamate.prediction", "duckdb", "pydantic"]
)
def test_cli_startup_import_failure_cannot_bypass_emergency_boundary(tmp_path, blocked):
    import subprocess
    import sys

    root = inputs(tmp_path)
    output = tmp_path / "out"
    launcher = tmp_path / "blocked_import.py"
    launcher.write_text(
        """import builtins
import sys
original = builtins.__import__
blocked = sys.argv[1]
def guard(name, *args, **kwargs):
    if name == blocked or name.startswith(blocked + "."):
        raise ImportError("synthetic blocked import")
    return original(name, *args, **kwargs)
builtins.__import__ = guard
from datamate.cli import main
sys.argv = ["datamate", "predict", "--input", sys.argv[2], "--output", sys.argv[3]]
raise SystemExit(main())
""",
        encoding="utf-8",
    )
    child = subprocess.run(
        [sys.executable, str(launcher), blocked, str(root), str(output)],
        capture_output=True,
        timeout=20,
    )
    assert child.returncode == 0, child.stderr
    assert len(results(output)) == 3


def test_failsafe_reports_routing_limit_as_incomplete_coverage(tmp_path, monkeypatch):
    import json

    import datamate.prediction_failsafe as module

    root = inputs(tmp_path, 1)
    with (root / "questions.jsonl").open("a") as handle:
        handle.write(json.dumps({"id": "large", "question": "x" * 1024}) + "\n")
    monkeypatch.setattr(module, "MAX_ROUTING_LINE", 512)
    config = tmp_path / "broken.yaml"
    config.write_text("[broken")
    outcome = module.submission_predict(root, tmp_path / "out", config_path=config)
    assert not outcome["valid"]
    assert outcome["coverage_complete"] is False
    assert outcome["routing_limit_lines"] == 1
