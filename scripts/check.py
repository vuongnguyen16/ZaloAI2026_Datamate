"""One local/CI gate. Uses only the active project environment."""

import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from harness import git_value, source_snapshot

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    # Keep test scratch in the writable workspace, independent of host TEMP ACLs.
    runs = ROOT / "runs"
    runs.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    scratch = Path(tempfile.mkdtemp(prefix=f"cpu-check-{stamp}-", dir=runs))
    env = {
        **os.environ,
        "OMP_NUM_THREADS": "2",
        "OPENBLAS_NUM_THREADS": "2",
        "TEMP": str(scratch),
        "TMP": str(scratch),
        "PYTHONIOENCODING": "utf-8",
    }
    snapshot = source_snapshot(ROOT)
    status = git_value(ROOT, "status", "--porcelain")
    report = {
        "schema_version": 1,
        "kind": "cpu",
        "status": "running",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": [sys.executable, "scripts/check.py"],
        "commit": git_value(ROOT, "rev-parse", "HEAD"),
        "dirty": None if status is None else bool(status),
        "source_fingerprint": snapshot["fingerprint"],
        "source_files_sha256": snapshot["files"],
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "tools": {tool: version(tool) for tool in ("ruff", "pytest")},
        },
        "stages": [],
        "gpu": "not_tested",
        "modal_model": "not_tested",
        "pa": "not_evaluated",
    }
    record_path = scratch / "gate.json"

    def save():
        record_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    save()
    commands = (
        ("ruff_check", ["-m", "ruff", "check", "."]),
        ("ruff_format", ["-m", "ruff", "format", "--check", "."]),
        (
            "pytest",
            [
                "-m",
                "pytest",
                "-q",
                "-m",
                "not gpu and not modal",
                "--basetemp",
                str(scratch / "pytest"),
                "-o",
                f"cache_dir={scratch / 'cache'}",
            ],
        ),
    )
    exit_code = 0
    for name, arguments in commands:
        command = [sys.executable, *arguments]
        log_path = scratch / f"{name}.log"
        stage = {
            "name": name,
            "command": command,
            "log": log_path.relative_to(ROOT).as_posix(),
            "status": "running",
        }
        report["stages"].append(stage)
        save()
        started = time.perf_counter()
        with log_path.open("w", encoding="utf-8") as log:
            try:
                result = subprocess.run(
                    command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT
                )
                exit_code = result.returncode
            except KeyboardInterrupt:
                exit_code = 130
                log.write("CPU gate interrupted\n")
            except OSError as exc:
                exit_code = 1
                log.write(f"Unable to start stage: {exc}\n")
        print(log_path.read_text("utf-8", errors="replace"), end="", flush=True)
        stage.update(
            exit_code=exit_code,
            status="passed" if exit_code == 0 else "failed",
            duration_seconds=time.perf_counter() - started,
        )
        save()
        if exit_code:
            break
    report["source_changed_during_gate"] = (
        source_snapshot(ROOT)["fingerprint"] != snapshot["fingerprint"]
    )
    if report["source_changed_during_gate"] and exit_code == 0:
        exit_code = 1
    report.update(
        status="passed" if exit_code == 0 else "failed",
        exit_code=exit_code,
        finished_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    save()
    print(f"CPU {report['status']}; GPU not_tested; PA not_evaluated")
    print(f"Evidence: {record_path.relative_to(ROOT).as_posix()}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
