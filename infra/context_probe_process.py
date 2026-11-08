"""P2-only subprocess diagnostics, importable without Modal/GPU dependencies."""

import json
import subprocess

from datamate.probe_diagnostics import sanitize_diagnostic
from infra.probe_process import atomic_json


def verify_context_snapshot(candidate, target, checkpoint):
    code = "import json,sys; from pathlib import Path; from datamate.model_probe import verify_snapshot; verify_snapshot(Path(sys.argv[1]),json.loads(sys.argv[2]))"
    try:
        subprocess.run(
            [
                "/opt/p1/runtime/.venv/bin/python",
                "-c",
                code,
                str(target),
                json.dumps(candidate["files"]),
            ],
            check=True,
            timeout=240,
            capture_output=True,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        raw = getattr(exc, "stderr", None) or type(exc).__name__
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        diagnostic = sanitize_diagnostic(raw)[:4096]
        atomic_json(
            checkpoint,
            {
                "status": "snapshot_verification_failed",
                "error_type": type(exc).__name__,
                "diagnostic": diagnostic,
            },
        )
        raise ValueError(f"snapshot verification failed: {diagnostic}") from None
