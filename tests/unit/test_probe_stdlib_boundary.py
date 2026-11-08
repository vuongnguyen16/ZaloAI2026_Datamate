import os
import subprocess
import sys
from pathlib import Path


def test_outer_probe_helpers_import_without_any_site_packages():
    root = Path(__file__).resolve().parents[2]
    env = os.environ | {"PYTHONPATH": os.pathsep.join([str(root), str(root / "src")])}
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "from infra.context_probe_process import verify_context_snapshot; from infra.probe_process import run_child; print('stdlib boundary ready')",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "stdlib boundary ready"
