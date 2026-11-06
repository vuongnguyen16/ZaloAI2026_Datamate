import json
import sys
from pathlib import Path


def test_child_process_preserves_logs_and_records_memory_without_retry(tmp_path):
    from infra.probe_process import run_child

    result = run_child(
        [
            sys.executable,
            "-c",
            "import sys; print('hello'); print('diagnostic', file=sys.stderr)",
        ],
        tmp_path,
        timeout=10,
        sample_memory=lambda: 1024,
    )
    assert result["exit_code"] == 0
    assert result["cleaned_up"] is True
    assert result["peak_memory_bytes"] == 1024
    assert result["memory_sample_count"] > 0
    assert "hello" in (tmp_path / "stdout.log").read_text()
    assert "diagnostic" in (tmp_path / "stderr.log").read_text()


def test_child_timeout_is_a_failure_with_cleanup_evidence(tmp_path):
    from infra.probe_process import run_child

    result = run_child(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        tmp_path,
        timeout=0.1,
        sample_memory=lambda: 1024,
    )
    assert result["timed_out"] is True
    assert result["exit_code"] != 0
    assert result["cleaned_up"] is True


def test_gpu_worker_request_rejects_answers_and_outside_model_paths():
    from datamate.probe_fixtures import build_cases, inference_cases
    from infra.p1_runtime.generate import validate_request

    config = json.loads(Path("manifests/models.json").read_text())["probe_candidates"][
        0
    ]
    request = {
        "repository": config["repository"],
        "revision": config["full_commit_revision"],
        "model_dir": "/weights/Qwen--Qwen3-14B/" + config["full_commit_revision"],
        "cases": inference_cases(build_cases()),
    }
    validate_request(request)
    import pytest

    with pytest.raises(ValueError):
        validate_request(request | {"cases": build_cases()})
    with pytest.raises(ValueError):
        validate_request(request | {"model_dir": "/tmp/another-model"})


def test_decoder_schema_rejects_observed_cross_type_answers():
    from jsonschema import Draft202012Validator

    from infra.p1_runtime.generate import output_schema

    validator = Draft202012Validator(output_schema())
    for record in (
        {"id": "fixture", "type": "table", "answer": ["mã", "số"]},
        {"id": "fixture", "type": "unanswerable", "answer": ""},
        {"id": "fixture", "type": "abstain", "answer": "abstain"},
    ):
        assert not validator.is_valid(record)
    for record in (
        {"id": "fixture", "type": "table", "answer": {"columns": ["x"], "rows": [[1]]}},
        {"id": "fixture", "type": "unanswerable"},
        {"id": "fixture", "type": "abstain"},
    ):
        assert validator.is_valid(record)
