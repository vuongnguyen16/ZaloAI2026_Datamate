import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from datamate.binding_proposals import make_case


def setup_cli(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "proposal_cli", root / "scripts/p2_binding_proposals.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    now = datetime(2026, 11, 8, tzinfo=timezone.utc)
    source, split, profile, payload = [
        tmp_path / n for n in ("source", "split", "profile", "payload")
    ]
    for folder in (source, split, profile, payload):
        folder.mkdir()
    case = make_case(
        "source",
        "known source",
        [],
        None,
        dict(code_sha256="a" * 64, model_revision="b" * 40, rulebook_sha256="c" * 64),
    )
    proof = dict(
        source=str(source),
        split=str(split),
        profile_index=str(profile / "profile.json"),
    )
    for file, value in [("provenance-local.json", proof), ("payload.json", [case])]:
        (payload / file).write_text(json.dumps(value), encoding="utf-8")
    billing = tmp_path / "billing.json"
    billing.write_text(
        json.dumps(
            dict(available_usd=30, checked_at=now.isoformat(), source="user-confirmed")
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("MODAL_PROFILE", "vuonghungnguyen07")
    monkeypatch.setattr(module, "build_payload", lambda _: ([case], proof))
    args = [
        "run",
        "--payload-dir",
        str(payload),
        "--billing-json",
        str(billing),
        "--output",
        str(tmp_path / "out"),
    ]
    return module, case, now, payload, args


def test_failed_cloud_envelope_leaves_no_cached_outputs(tmp_path, monkeypatch):
    module, _, now, payload, args = setup_cli(tmp_path, monkeypatch)

    def failed_transport(*_):
        return dict(
            network_blocked=True,
            weights_read_only=True,
            snapshot_verified=True,
            contexts=[
                dict(
                    status="completed",
                    exit_code=-9,
                    timed_out=True,
                    cleaned_up=False,
                    peak_memory_bytes=40 * 1024**3,
                    records=[],
                )
            ],
        )

    with pytest.raises(ValueError):
        module.main(
            args,
            account_reader=lambda: dict(
                workspace="vuonghungnguyen07", user="vuonghungnguyen07"
            ),
            transport_factory=lambda: failed_transport,
            now=now,
        )
    assert not list((payload / "cache").glob("*.json"))
    assert (tmp_path / "out/result.json").is_file()


def test_foreign_cache_identity_is_rejected_before_transport(tmp_path, monkeypatch):
    module, case, now, payload, args = setup_cli(tmp_path, monkeypatch)
    (payload / "cache").mkdir()
    (payload / "cache" / (case["id"] + ".json")).write_text(
        json.dumps(
            dict(
                case_id="foreign",
                finish_reason="stop",
                text='{"choice":"unknown","quote":"","bindings":[]}',
            )
        ),
        encoding="utf-8",
    )
    called = []
    with pytest.raises(ValueError):
        module.main(
            args,
            account_reader=lambda: dict(
                workspace="vuonghungnguyen07", user="vuonghungnguyen07"
            ),
            transport_factory=lambda: called.append(True),
            now=now,
        )
    assert not called


def test_rejected_completed_cache_is_reported_without_reinference(
    tmp_path, monkeypatch
):
    module, case, now, payload, args = setup_cli(tmp_path, monkeypatch)
    (payload / "cache").mkdir()
    (payload / "cache" / (case["id"] + ".json")).write_text(
        json.dumps(
            dict(
                case_id=case["id"],
                finish_reason="length",
                text='{"choice":"unknown","quote":"","bindings":[]}',
            )
        ),
        encoding="utf-8",
    )
    called = []
    assert (
        module.main(
            args,
            account_reader=lambda: dict(
                workspace="vuonghungnguyen07", user="vuonghungnguyen07"
            ),
            transport_factory=lambda: called.append(True),
            now=now,
        )
        == 0
    )
    assert not called
    result = json.loads((tmp_path / "out/validation.json").read_text("utf-8"))
    assert (
        result["cache_hits"] == 1
        and result["records"][0]["review_status"] == "rejected_output"
    )
