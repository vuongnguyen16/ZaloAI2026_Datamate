"""Group G CPU smoke only. Explicit allowlist prevents uploading the BTC kit.

Run via the local entrypoint so profile and declared budget are checked first.
No GPU, weights or business data are attached to this app.
"""

import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import modal
import yaml

ROOT = Path(__file__).resolve().parents[1]
REMOTE_ROOT = "/opt/datamate"
app = modal.App("datamate-s00-cpu")
image = modal.Image.debian_slim(python_version="3.11.18").pip_install(
    "uv==0.13.6", "pyyaml==6.0.3"
)
for name in ("pyproject.toml", "uv.lock", "README.md"):
    image = image.add_local_file(ROOT / name, f"{REMOTE_ROOT}/{name}", copy=True)
image = (
    image.add_local_dir(
        ROOT / "src",
        f"{REMOTE_ROOT}/src",
        copy=True,
        ignore=["**/__pycache__/**", "**/*.pyc"],
    )
    .add_local_dir(
        ROOT / "tests/fixtures/synthetic",
        f"{REMOTE_ROOT}/tests/fixtures/synthetic",
        copy=True,
    )
    .add_local_file(
        ROOT / "configs/smoke.yaml", f"{REMOTE_ROOT}/configs/smoke.yaml", copy=True
    )
    .run_commands(
        f"cd {REMOTE_ROOT} && UV_INDEX_URL=https://pypi.org/simple "
        "UV_DEFAULT_INDEX=https://pypi.org/simple uv sync --locked --no-dev --no-group cloud"
    )
)


@app.function(
    image=image,
    cpu=1,
    memory=512,
    min_containers=0,
    buffer_containers=0,
    max_containers=1,
    scaledown_window=2,
    timeout=120,
    startup_timeout=300,
    retries=0,
    block_network=True,
    include_source=False,
    serialized=True,
)
def cpu_smoke() -> dict:
    started = time.perf_counter()
    directory = Path(REMOTE_ROOT)
    config = yaml.safe_load((directory / "configs/smoke.yaml").read_text())
    config.update(
        input_dir=str(directory / "tests/fixtures/synthetic"),
        output_root="/tmp/datamate-runs",
        local_cpu_threads=1,
    )
    config_path = Path("/tmp/datamate-smoke.yaml")
    config_path.write_text(yaml.safe_dump(config))
    # Probe outbound connectivity explicitly; disconnected inference must not depend on it.
    try:
        urllib.request.urlopen("https://example.com", timeout=3).close()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        network_probe = {
            "outbound_request_failed": True,
            "error_type": type(exc).__name__,
        }
    else:
        raise RuntimeError("outbound network unexpectedly available")
    command = subprocess.run(
        [f"{REMOTE_ROOT}/.venv/bin/datamate", "smoke", "--config", str(config_path)],
        text=True,
        capture_output=True,
        timeout=60,
        env={**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"},
    )
    if command.returncode:
        raise RuntimeError(f"CPU smoke failed: {command.stderr[-3000:]}")
    run_dir = Path(command.stdout.strip().splitlines()[-1])
    files = {
        p.relative_to(run_dir).as_posix(): p.read_text("utf-8")
        for p in run_dir.rglob("*")
        if p.is_file()
    }
    outputs = [json.loads(line) for line in files["submission.jsonl"].splitlines()]
    expected = [
        {"id": "synthetic_sum", "type": "number", "answer": 12.35},
        {"id": "synthetic_code", "type": "string", "answer": "0012"},
    ]
    if outputs != expected:
        raise RuntimeError("remote smoke differs from hand-calculated fixture")
    return {
        "files": files,
        "network_probe": network_probe,
        "duration_seconds": time.perf_counter() - started,
        "gpu": "not_used",
        "pa": "not_evaluated",
    }


@app.local_entrypoint()
def main():
    settings = yaml.safe_load((ROOT / "configs/modal_dev.yaml").read_text("utf-8"))
    if os.environ.get("MODAL_PROFILE") != settings["profile"]:
        raise ValueError(
            "set MODAL_PROFILE to the project's explicit profile before launching"
        )
    budget = settings.get("budget_usd_per_experiment")
    if not isinstance(budget, (int, float)) or budget <= 0:
        raise ValueError("positive authorized experiment budget required")
    result = cpu_smoke.remote()
    destination = ROOT / "runs" / f"modal-cpu-{time.time_ns()}"
    destination.mkdir(parents=True, exist_ok=False)
    files = result.pop("files")
    for name, content in files.items():
        path = destination / name
        if destination.resolve() not in path.resolve().parents:
            raise ValueError("invalid returned artifact path")
        path.parent.mkdir(parents=True, exist_ok=True)
        # Preserve remote bytes on Windows; text mode would translate LF to CRLF.
        path.write_bytes(content.encode("utf-8"))
    result.update(
        image_id=image.object_id,
        infra_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        profile=settings["profile"],
        workspace=settings["workspace"],
        budget_usd_per_experiment=budget,
        artifact_sha256={
            name: hashlib.sha256(content.encode()).hexdigest()
            for name, content in files.items()
        },
        billing_usd="not_yet_available; check Modal dashboard",
    )
    (destination / "remote_summary.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(destination)
