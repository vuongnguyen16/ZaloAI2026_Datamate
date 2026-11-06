import base64
import json

import pytest


def test_cloud_image_emits_sdk_series_and_installs_exact_worker_python():
    from infra.modal_model_probe import build_images

    calls, commands, environment = [], [], {}

    class Image:
        @classmethod
        def debian_slim(cls, **kwargs):
            return cls()

        @classmethod
        def from_registry(cls, base, *, add_python):
            if add_python.count(".") != 1:
                raise ValueError("SDK only accepts major.minor")
            calls.append((base, add_python))
            return cls()

        def pip_install(self, *args):
            return self

        def add_local_file(self, *args, **kwargs):
            return self

        def env(self, *args, **kwargs):
            environment.update(args[0])
            return self

        def run_commands(self, *args):
            commands.extend(args)
            return self

    build_images(
        Image, {"base_image": "nvidia/cuda@sha256:" + "a" * 64, "python": "3.11.18"}
    )
    assert calls == [("nvidia/cuda@sha256:" + "a" * 64, "3.11")]
    assert any("uv python install 3.11.18" in command for command in commands)
    assert all(
        "--python 3.11.18" in command for command in commands if "uv sync" in command
    )
    assert environment["UV_INDEX_URL"] == "https://pypi.org/simple"
    assert environment["UV_DEFAULT_INDEX"] == "https://pypi.org/simple"


def test_deadline_accounts_for_hashing_and_leaves_return_reserve():
    from infra.probe_process import remaining_timeout

    assert remaining_timeout(100.0, 1200, remaining_rounds=2, now=400.0) == 405.0
    assert remaining_timeout(100.0, 1200, remaining_rounds=1, now=1000.0) == 210.0
    with pytest.raises(TimeoutError):
        remaining_timeout(100.0, 1200, remaining_rounds=1, now=1220.0)


def test_atomic_checkpoint_and_corrupt_checkpoint_preserve_bytes(tmp_path, monkeypatch):
    import infra.probe_process as process

    path = tmp_path / "output.json"
    process.atomic_json(path, {"records": ["complete"]})
    monkeypatch.setattr(
        process.os,
        "replace",
        lambda *args: (_ for _ in ()).throw(OSError("synthetic disk failure")),
    )
    with pytest.raises(OSError):
        process.atomic_json(path, {"records": ["new"]})
    assert json.loads(path.read_text())["records"] == ["complete"]
    path.write_bytes(b'{"incomplete":\xff')
    raw = process.read_checkpoint(path)
    assert base64.b64decode(raw["checkpoint_raw_base64"]) == path.read_bytes()
    assert raw["records"] == []


def test_round_is_committed_before_caller_can_start_next_round(tmp_path):
    from infra.probe_process import checkpoint_round

    calls = []

    def commit():
        calls.append(json.loads((tmp_path / "round.json").read_text())["pid"])

    checkpoint_round(tmp_path, {"pid": 123, "records": []}, commit)
    assert calls == [123]


def test_startup_failure_records_app_id_and_sanitized_diagnostic():
    from infra.modal_model_probe import failure_event

    class App:
        app_id = "ap-synthetic"

    event = failure_event(
        App(),
        "startup",
        RuntimeError(
            "bad image token_secret=very-private https://example.com/path?token=also-private"
        ),
    )
    assert event["app_id"] == "ap-synthetic"
    assert event["phase"] == "startup_failed"
    assert "bad image" in event["message"]
    assert (
        "very-private" not in event["message"]
        and "also-private" not in event["message"]
    )
