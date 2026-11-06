import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def entrypoint():
    spec = importlib.util.spec_from_file_location(
        "p2_context_probe", ROOT / "scripts/p2_context_probe.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bad_billing_does_not_create_transport(tmp_path, monkeypatch):
    mod = entrypoint()
    monkeypatch.setenv("MODAL_PROFILE", "vuonghungnguyen07")
    billing = tmp_path / "billing.json"
    billing.write_text(
        json.dumps(
            {
                "available_usd": 0,
                "source": "user-confirmed",
                "checked_at": "2026-11-07T00:00:00+00:00",
            }
        )
    )
    called = []
    with pytest.raises(ValueError, match="billing"):
        mod.main(
            ["check", "--billing-json", str(billing)],
            account_reader=lambda: {
                "workspace": "vuonghungnguyen07",
                "user": "vuonghungnguyen07",
            },
            transport_factory=lambda: called.append(True),
            now=datetime(2026, 11, 7, tzinfo=timezone.utc),
        )
    assert called == []


def test_running_p2_app_denied_but_stopped_allowed():
    mod = entrypoint()
    with pytest.raises(ValueError, match="existing"):
        mod.check_apps(
            [{"Description": "datamate-p2-context-probe", "State": "ephemeral"}]
        )
    mod.check_apps([{"Description": "datamate-p2-context-probe", "State": "stopped"}])


def test_remote_payload_rejects_gold_and_unbounded_messages():
    from datamate.intent_probe import make_case, validate_cases

    case = make_case(
        {
            "id": "synthetic_q",
            "business_id": "synthetic_b",
            "question": "Total?",
            "as_of_date": "2026-11-07",
        },
        {"tables": []},
    )
    validate_cases([case] * 0 + [case])
    for bad in [
        [case | {"answer": 1}],
        [case, case],
        [case | {"messages": [{"role": "user", "content": "x" * 300000}]}],
    ]:
        with pytest.raises(ValueError):
            validate_cases(bad)


def test_image_additions_only_contain_code():
    from infra.modal_context_probe import extra_image_files

    files = extra_image_files()
    assert {p.name for p, _ in files} == {
        "intent_probe.py",
        "scoring.py",
        "context_generate.py",
        "context_probe_process.py",
    }
    assert all(
        "data" not in p.relative_to(ROOT).parts and p.suffix == ".py" for p, _ in files
    )


def test_prepare_checks_frozen_data_prefix_and_never_reads_gold(tmp_path, monkeypatch):
    from datamate.profile.engine import code_hash

    mod = entrypoint()
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests/split_lock.json").write_text(
        json.dumps(
            {
                "artifact_directory": str(tmp_path / "frozen"),
                "manifest_sha256": "0" * 64,
            }
        )
    )
    generation = tmp_path / "profiles"
    generation.mkdir()
    business = "synthetic_b"
    profile = {
        "business_id": business,
        "provenance": {
            "ingest_fingerprint": "fingerprint",
            "files": [{"path": "orders.csv", "sha256": "1" * 64}],
        },
    }
    schema = {
        "business_id": business,
        "ingest_fingerprint": "fingerprint",
        "tables": [],
    }
    entry = {"business_id": business, "valid": True}
    for kind, obj in [("profile", profile), ("schema", schema)]:
        path = generation / (kind + "-business.json")
        path.write_text(json.dumps(obj))
        entry[kind] = {"path": str(path), "sha256": mod.sha(path.read_bytes())}
    index = generation / "profile.json"
    index.write_text(
        json.dumps(
            {
                "valid": True,
                "profile_code_sha256": code_hash(),
                "gold_content_read": False,
                "businesses": [entry],
            }
        )
    )
    manifest = {
        "source": {
            "input_dir": str(tmp_path / "raw"),
            "files": {"data/synthetic_b/orders.csv": "1" * 64},
        },
        "groups": [
            {"group_id": "synthetic_c", "partition": "dev", "businesses": [business]}
        ],
    }
    monkeypatch.setattr(mod, "open_split", lambda *a, **k: (manifest, {}))
    monkeypatch.setattr(mod, "authorize_access", lambda *a, **k: ["synthetic_q"])
    reads = []

    def read(*args):
        reads.append(args[3])
        return {
            "synthetic_q": {
                "id": "synthetic_q",
                "business_id": business,
                "question": "Total?",
                "as_of_date": "2026-11-07",
            }
        }, {}

    monkeypatch.setattr(mod, "read_scoped", read)
    assert mod.prepare(index, tmp_path / "payload")["cases"] == 1
    assert reads == ["questions"]
    manifest["source"]["files"]["data/synthetic_b/orders.csv"] = "2" * 64
    with pytest.raises(ValueError, match="source"):
        mod.prepare(index, tmp_path / "bad")
