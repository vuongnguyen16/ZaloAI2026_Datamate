"""P1 cloud transport. No SDK import or resource creation at module import."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cloud(config: dict, model: dict, cases: list[dict], record_event) -> dict:
    import modal

    runtime = json.loads((ROOT / "configs/p1_runtime.json").read_text("utf-8"))
    base = runtime["base_image"]
    if not base.startswith("nvidia/cuda@sha256:") or len(base.rsplit(":", 1)[-1]) != 64:
        raise ValueError("immutable CUDA image digest required")
    app = modal.App("datamate-p1-model-probe")
    volume = modal.Volume.from_name(
        "datamate-p1-model-weights-v1", create_if_missing=True
    )
    common = modal.Image.debian_slim(python_version="3.11.18").pip_install("uv==0.13.6")
    gpu = modal.Image.from_registry(base, add_python="3.11.18").pip_install(
        "uv==0.13.6"
    )

    def prepare(image, group):
        for name in ("pyproject.toml", "uv.lock"):
            image = image.add_local_file(
                ROOT / "infra/p1_runtime" / name, f"/opt/p1/runtime/{name}", copy=True
            )
        for name in ("__init__.py", "model_probe.py"):
            image = image.add_local_file(
                ROOT / "src/datamate" / name, f"/opt/p1/src/datamate/{name}", copy=True
            )
        return image.env(
            {"PYTHONPATH": "/opt/p1/src", "UV_PYTHON_DOWNLOADS": "never"}
        ).run_commands(
            f"cd /opt/p1/runtime && uv sync --locked --only-group {group} --no-install-project --python 3.11"
        )

    common, gpu = prepare(common, "staging"), prepare(gpu, "gpu")
    gpu = gpu.add_local_file(
        ROOT / "infra/probe_process.py", "/opt/p1/probe_process.py", copy=True
    )
    gpu = gpu.add_local_file(
        ROOT / "infra/p1_runtime/generate.py", "/opt/p1/generate.py", copy=True
    )
    gpu = gpu.env(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "VLLM_NO_USAGE_STATS": "1",
            "DO_NOT_TRACK": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
        }
    )

    @app.function(
        image=common,
        volumes={"/weights": volume},
        cpu=2,
        memory=16384,
        max_containers=1,
        min_containers=0,
        buffer_containers=0,
        scaledown_window=2,
        timeout=config["staging_timeout_seconds"],
        startup_timeout=600,
        retries=0,
        include_source=False,
        serialized=True,
    )
    def stage(candidate):
        import subprocess

        target = (
            Path("/weights")
            / candidate["repository"].replace("/", "--")
            / candidate["full_commit_revision"]
        )
        marker = target / ".complete.json"
        cached = marker.is_file()
        if not cached:
            target.mkdir(parents=True, exist_ok=True)
            # Execute the dependency-locked interpreter, never a host environment.
            payload = json.dumps(
                {
                    "repo": candidate["repository"],
                    "revision": candidate["full_commit_revision"],
                    "directory": str(target),
                    "files": list(candidate["files"]),
                }
            )
            code = "import json,sys; from huggingface_hub import snapshot_download; p=json.loads(sys.argv[1]); snapshot_download(repo_id=p['repo'],revision=p['revision'],local_dir=p['directory'],allow_patterns=p['files'],max_workers=4)"
            subprocess.run(
                ["/opt/p1/runtime/.venv/bin/python", "-c", code, payload],
                check=True,
                timeout=config["staging_timeout_seconds"] - 30,
            )
        # Pydantic is in the locked environment rather than Modal's interpreter.
        validation = "import json,sys; from pathlib import Path; from datamate.model_probe import verify_snapshot; print(json.dumps(verify_snapshot(Path(sys.argv[1]),json.loads(sys.argv[2]))))"
        result = subprocess.run(
            [
                "/opt/p1/runtime/.venv/bin/python",
                "-c",
                validation,
                str(target),
                json.dumps(candidate["files"]),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        hashes = json.loads(result.stdout)
        marker.write_text(
            json.dumps(
                {
                    "repository": candidate["repository"],
                    "revision": candidate["full_commit_revision"],
                    "files": hashes,
                }
            )
        )
        volume.commit()
        return {"snapshot_path": str(target), "hashes": hashes, "cached": cached}

    @app.function(
        image=gpu,
        gpu=config["gpu"],
        volumes={"/weights": volume.with_mount_options(read_only=True)},
        cpu=8,
        memory=65536,
        max_containers=1,
        min_containers=0,
        buffer_containers=0,
        scaledown_window=2,
        timeout=config["gpu_timeout_seconds"],
        startup_timeout=config["startup_timeout_seconds"],
        retries=0,
        block_network=True,
        include_source=False,
        serialized=True,
    )
    def probe(candidate, payload):
        import os
        import subprocess
        import sys
        import tempfile
        import urllib.error
        import urllib.request
        import uuid

        sys.path.insert(0, "/opt/p1")
        from probe_process import run_child

        target = (
            Path("/weights")
            / candidate["repository"].replace("/", "--")
            / candidate["full_commit_revision"]
        )
        directory = Path(tempfile.mkdtemp(prefix="p1-probe-"))
        check_code = "import json,sys; from pathlib import Path; from datamate.model_probe import verify_snapshot; print(json.dumps(verify_snapshot(Path(sys.argv[1]),json.loads(sys.argv[2]))))"
        subprocess.run(
            [
                "/opt/p1/runtime/.venv/bin/python",
                "-c",
                check_code,
                str(target),
                json.dumps(candidate["files"]),
            ],
            check=True,
            timeout=300,
        )
        try:
            urllib.request.urlopen("https://example.com", timeout=3).close()
        except (urllib.error.URLError, TimeoutError, OSError):
            blocked = True
        else:
            blocked = False
        write_probe = target / (".write-probe-" + uuid.uuid4().hex)
        try:
            with write_probe.open("xb") as stream:
                stream.write(b"synthetic probe")
        except OSError:
            read_only = True
        else:
            read_only = False
            write_probe.unlink()
        if not blocked or not read_only:
            raise ValueError("offline or read-only boundary failed")
        request = {
            "repository": candidate["repository"],
            "revision": candidate["full_commit_revision"],
            "model_dir": str(target),
            "config": config,
            "cases": payload,
        }
        request_path = directory / "request.json"
        request_path.write_text(
            json.dumps(request, ensure_ascii=False), encoding="utf-8"
        )

        def sample():
            try:
                measured = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=memory.used",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=True,
                )
                return int(measured.stdout.strip().splitlines()[0]) * 1024**2
            except (ValueError, OSError, subprocess.SubprocessError):
                return None

        rounds = []
        for number in (1, 2):
            folder = directory / f"round-{number}"
            folder.mkdir()
            output = folder / "output.json"
            metrics = run_child(
                [
                    "/opt/p1/runtime/.venv/bin/python",
                    "/opt/p1/generate.py",
                    "--request",
                    str(request_path),
                    "--output",
                    str(output),
                ],
                folder,
                timeout=(config["gpu_timeout_seconds"] - 60) / 2,
                sample_memory=sample,
            )
            result = (
                json.loads(output.read_text("utf-8"))
                if output.is_file()
                else {"records": []}
            )
            result.update(metrics)
            for log in ("stdout", "stderr"):
                result[log] = (folder / f"{log}.log").read_text(
                    "utf-8", errors="replace"
                )[-200000:]
            rounds.append(result)
            if not metrics["cleaned_up"] or metrics["exit_code"]:
                break
        capability = (
            rounds[0].get("runtime", {}).get("device_capability") if rounds else None
        )
        telemetry = {
            "transport": "modal",
            "device_capability": capability,
            "network_blocked": blocked,
            "weights_read_only": read_only,
            "snapshot_verified": True,
            "runtime_pins_verified": len(rounds) == 2
            and all(r.get("runtime_pins_verified") is True for r in rounds),
            "peak_memory_bytes": max(
                (r.get("peak_memory_bytes", 0) for r in rounds), default=0
            ),
            "memory_sample_count": sum(r.get("memory_sample_count", 0) for r in rounds),
            "memory_method": "sampled total-device nvidia-smi MiB at approximately50ms+command latency; not a physical partition",
            "worker_uid": os.getuid(),
        }
        return {"rounds": rounds, "telemetry": telemetry}

    with modal.enable_output(), app.run():
        record_event(
            {
                "phase": "app_started",
                "app_id": app.app_id,
                "base_image": base,
                "staging_image_id": common.object_id,
                "gpu_image_id": gpu.object_id,
            }
        )
        staged = stage.remote(model)
        record_event(
            {
                "phase": "staging_complete",
                "app_id": app.app_id,
                "cached": staged["cached"],
            }
        )
        result = probe.remote(model, cases)
        result.update(
            staging=staged,
            app_id=app.app_id,
            base_image=base,
            staging_image_id=common.object_id,
            gpu_image_id=gpu.object_id,
            billing_usd="not_yet_available; inspect Modal dashboard",
        )
        return result
