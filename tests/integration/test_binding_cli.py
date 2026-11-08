import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


def entry():
    path = Path(__file__).resolve().parents[2] / "scripts/p2_binding_audit.py"
    spec = importlib.util.spec_from_file_location("binding_cli", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("mode", ["worker", "diagnose-worker", "diagnose"])
def test_worker_denies_nondev_before_reader_or_output(tmp_path, mode):
    mod = entry()
    called = []
    scope = dict(
        source=tmp_path / "raw",
        split=tmp_path / "frozen",
        businesses={"synthetic_dev"},
        groups={},
    )
    with pytest.raises(PermissionError):
        mod.main(
            [
                mode,
                "--profile-index",
                str(tmp_path / "no-profile.json"),
                "--business",
                "synthetic_cal",
                "--output",
                str(tmp_path / "output"),
            ],
            scope_reader=lambda: scope,
            auditor=lambda *a, **k: called.append(True),
        )
    assert called == [] and not (tmp_path / "output").exists()


def test_cli_has_no_partition_override():
    with pytest.raises(SystemExit):
        entry().main(["worker", "--partition", "holdout"])


def test_pending_lexicon_stops_before_auditor_or_output(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "rulebook.md").write_text("rules", encoding="utf-8")
    lexicon = tmp_path / "lexicon.json"
    lexicon.write_text(
        json.dumps(
            dict(
                version=1,
                partition="dev",
                rulebook_sha256=hashlib.sha256(b"rules").hexdigest(),
                review=dict(state="pending"),
            )
        ),
        encoding="utf-8",
    )
    called = []
    output = tmp_path / "out"
    with pytest.raises(ValueError, match="approval"):
        entry().main(
            [
                "worker",
                "--profile-index",
                str(tmp_path / "profile/index.json"),
                "--output",
                str(output),
                "--business",
                "dev",
                "--status-lexicon",
                str(lexicon),
                "--lexicon-sha256",
                hashlib.sha256(lexicon.read_bytes()).hexdigest(),
            ],
            scope_reader=lambda: dict(
                source=raw, split=tmp_path / "split", businesses={"dev"}, groups={}
            ),
            auditor=lambda *a, **k: called.append(True),
        )
    assert not output.exists() and not called
