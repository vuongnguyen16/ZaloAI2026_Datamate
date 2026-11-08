import importlib.util
from pathlib import Path

import pytest


def test_review_worker_denies_nondevelopment_before_output(tmp_path):
    path = Path(__file__).resolve().parents[2] / "scripts/p2_semantic_review.py"
    spec = importlib.util.spec_from_file_location("semantic_cli", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    output = tmp_path / "out"
    with pytest.raises(PermissionError):
        mod.main(
            [
                "worker",
                "--profile-index",
                str(tmp_path / "missing"),
                "--business",
                "sealed",
                "--output",
                str(output),
            ],
            scope_reader=lambda: dict(businesses={"dev"}),
        )
    assert not output.exists()
