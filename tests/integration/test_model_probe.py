import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from datamate.model_probe import ModelCandidate, ProbeConfig

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 11, 6, 6, 53, 37, tzinfo=timezone.utc)


def inputs():
    import yaml

    config = ProbeConfig(
        **yaml.safe_load((ROOT / "configs/p1_probe.yaml").read_text("utf-8"))
    )
    candidates = json.loads((ROOT / "manifests/models.json").read_text("utf-8"))[
        "probe_candidates"
    ]
    model = ModelCandidate.model_validate(candidates[0])
    account = {"workspace": "vuonghungnguyen07", "user": "vuonghungnguyen07"}
    billing = {
        "available_usd": 30.0,
        "checked_at": NOW.isoformat(),
        "source": "user-confirmed",
    }
    return config, model, account, billing


def test_invalid_preflight_never_constructs_transport_or_output(tmp_path):
    from datamate.probe_runner import execute_probe

    config, model, account, billing = inputs()
    account["workspace"] = "wrong"

    def forbidden():
        pytest.fail("transport constructed before preflight")

    with pytest.raises(ValueError, match="account"):
        execute_probe(
            config,
            model,
            account,
            billing,
            profile_env="vuonghungnguyen07",
            transport_factory=forbidden,
            output_root=tmp_path / "runs",
            now=NOW,
        )
    assert not (tmp_path / "runs").exists()


def test_transport_failure_is_preserved_without_retry(tmp_path):
    from datamate.probe_runner import execute_probe

    config, model, account, billing = inputs()
    calls = []

    def transport(cfg, mdl, payload, record_event):
        calls.append(payload)
        record_event({"app_id": "synthetic-app", "phase": "staging"})
        assert all(set(case) == {"id", "prompt"} for case in payload)
        raise RuntimeError("synthetic transport failed")

    with pytest.raises(RuntimeError, match="synthetic"):
        execute_probe(
            config,
            model,
            account,
            billing,
            profile_env="vuonghungnguyen07",
            transport_factory=lambda: transport,
            output_root=tmp_path,
            now=NOW,
        )
    assert len(calls) == 1
    run = next(tmp_path.glob("p1-probe-*"))
    report = json.loads((run / "acceptance.json").read_text())
    assert report["g1_passed"] is False
    assert report["status"] == "failed"
    assert "synthetic transport failed" in report["message"]
    assert "RuntimeError" in report["traceback"]
    assert "synthetic-app" in (run / "events.jsonl").read_text()
    assert (run / "preflight.json").is_file()
    assert (run / "source.json").is_file()


def test_empty_fake_result_cannot_be_gpu_success(tmp_path):
    from datamate.probe_runner import execute_probe

    config, model, account, billing = inputs()
    result = {"rounds": [], "telemetry": {"transport": "fake"}}
    run = execute_probe(
        config,
        model,
        account,
        billing,
        profile_env="vuonghungnguyen07",
        transport_factory=lambda: lambda *args: result,
        output_root=tmp_path,
        now=NOW,
    )
    assert json.loads((run / "acceptance.json").read_text())["g1_passed"] is False
    assert json.loads((run / "raw_result.json").read_text()) == result


def test_module_imports_do_not_import_cloud_sdk_or_gpu_libraries():
    code = "import sys; import datamate.probe_runner; import infra.modal_model_probe; assert not any(n in sys.modules for n in ('modal','torch','vllm','transformers'))"
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=dict(os.environ),
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


def test_source_change_during_transport_is_recorded_and_rejected(tmp_path, monkeypatch):
    import datamate.probe_runner as runner

    monkeypatch.setattr(runner, "SOURCE_ROOT", tmp_path)
    monkeypatch.setattr(runner, "SOURCE_PATHS", ("sentinel.py",))
    sentinel = tmp_path / "sentinel.py"
    sentinel.write_text("before")

    def transport(*args):
        sentinel.write_text("after")
        return {"rounds": [], "telemetry": {"transport": "fake"}}

    config, model, account, billing = inputs()
    run = runner.execute_probe(
        config,
        model,
        account,
        billing,
        profile_env="vuonghungnguyen07",
        transport_factory=lambda: transport,
        output_root=tmp_path / "runs",
        now=NOW,
    )
    report = json.loads((run / "acceptance.json").read_text())
    assert report["source_changed"] is True
    assert report["g1_passed"] is False
    assert "source changed during probe" in report["errors"]
