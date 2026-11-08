import importlib.util
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
