import hashlib
import json
import platform
import subprocess
import uuid
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def git_output(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def new_run(output_root: Path, mode: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_root / f"{mode}-{stamp}-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "logs").mkdir()
    return run_dir


def manifest(root: Path, inputs: list[Path], mode: str, run_id: str) -> dict:
    code_paths = []
    for directory in ("src", "scripts", "infra", "configs", "tests/fixtures/synthetic"):
        code_paths.extend(
            p
            for p in (root / directory).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        )
    code_paths.extend(
        root / name
        for name in ("pyproject.toml", "uv.lock", "predict.sh")
        if (root / name).is_file()
    )
    code_hashes = {
        str(p.relative_to(root)).replace("\\", "/"): sha256(p)
        for p in sorted(code_paths)
    }
    status = git_output(root, "status", "--porcelain")
    diff = git_output(root, "diff", "HEAD")
    return {
        "run_id": run_id,
        "mode": mode,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "commit": git_output(root, "rev-parse", "HEAD"),
        "dirty": None if status is None else bool(status),
        "git_diff_sha256": hashlib.sha256(diff.encode()).hexdigest()
        if diff is not None
        else None,
        "source_files_sha256": code_hashes,
        "source_fingerprint": hashlib.sha256(
            json.dumps(code_hashes, sort_keys=True).encode()
        ).hexdigest(),
        "input_files_sha256": {str(p): sha256(p) for p in inputs},
        "lock_sha256": sha256(root / "uv.lock")
        if (root / "uv.lock").is_file()
        else None,
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "packages": {p: version(p) for p in ("duckdb", "pydantic", "pyyaml")},
        },
        "model": {"adapter": "fake" if mode == "smoke" else "none", "revision": None},
        "gpu": "not_tested",
        "pa": "not_evaluated",
    }
