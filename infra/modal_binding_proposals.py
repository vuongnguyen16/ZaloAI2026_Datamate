"""P2c proposal transport: allowlisted code, read-only existing weights, dev payload."""

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def extra_image_files():
    return [
        (ROOT / "src/datamate/intent_probe.py", "/opt/p1/src/datamate/intent_probe.py"),
        (
            ROOT / "src/datamate/binding_proposals.py",
            "/opt/p1/src/datamate/binding_proposals.py",
        ),
        (ROOT / "src/datamate/scoring.py", "/opt/p1/src/datamate/scoring.py"),
        (ROOT / "infra/p1_runtime/binding_generate.py", "/opt/p1/binding_generate.py"),
        (
            ROOT / "infra/context_probe_process.py",
            "/opt/p1/src/infra/context_probe_process.py",
        ),
    ]


def run_cloud(config, model, cases, record_event):
    import modal

    from datamate.binding_proposals import BindingProposalConfig, validate_cases
    from infra.modal_model_probe import build_images, failure_event

    BindingProposalConfig.model_validate(config)
    validate_cases(cases)
    runtime = json.loads((ROOT / "configs/p1_runtime.json").read_text("utf-8"))
    _, gpu = build_images(modal.Image, runtime)
    for source, target in extra_image_files():
        gpu = gpu.add_local_file(source, target, copy=True)
    app = modal.App("datamate-p2-binding-proposals")
    weights = modal.Volume.from_name(
        "datamate-p1-model-weights-v1", create_if_missing=False
    )
    evidence = modal.Volume.from_name(
        "datamate-p2-probe-evidence-v1", create_if_missing=True
    )
    key = uuid.uuid4().hex

    @app.function(
        image=gpu,
        gpu=config["gpu"],
        cpu=8,
        memory=65536,
        volumes={
            "/weights": weights.with_mount_options(read_only=True),
            "/evidence": evidence,
        },
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
    def probe(candidate, payload, evidence_key):
        import os
        import subprocess
        import tempfile
        import time
        import urllib.error
        import urllib.request

        from infra.probe_process import (
            atomic_json,
            read_checkpoint,
            remaining_timeout,
            run_child,
        )

        started = time.monotonic()
        target = (
            Path("/weights")
            / candidate["repository"].replace("/", "--")
            / candidate["full_commit_revision"]
        )
        directory = Path(tempfile.mkdtemp(prefix="p2-binding-"))
        persistent = Path("/evidence") / evidence_key
        persistent.mkdir(parents=True, exist_ok=False)
        from infra.context_probe_process import verify_context_snapshot

        try:
            verify_context_snapshot(candidate, target, persistent / "snapshot.json")
        except ValueError:
            evidence.commit()
            raise
        try:
            urllib.request.urlopen("https://example.com", timeout=3).close()
        except (urllib.error.URLError, TimeoutError, OSError):
            blocked = True
        else:
            blocked = False
        write_test = target / (".p2-write-probe-" + uuid.uuid4().hex)
        try:
            with write_test.open("xb") as stream:
                stream.write(b"probe")
        except OSError:
            read_only = True
        else:
            read_only = False
            write_test.unlink()
        if not blocked or not read_only:
            raise ValueError("offline/read-only boundary failed")

        def sample():
            try:
                value = subprocess.run(
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
                return int(value.stdout.strip().splitlines()[0]) * 1024**2
            except (ValueError, OSError, subprocess.SubprocessError):
                return None

        results = []
        for index, context in enumerate((4096,)):
            folder = directory / str(context)
            folder.mkdir()
            final = persistent / str(context)
            final.mkdir()
            request = dict(
                model_dir=str(target),
                config=config | {"max_model_len": context},
                cases=payload,
            )
            request_path = folder / "request.json"
            atomic_json(request_path, request)
            output = final / "output.json"
            metrics = run_child(
                [
                    "/opt/p1/runtime/.venv/bin/python",
                    "/opt/p1/binding_generate.py",
                    "--request",
                    str(request_path),
                    "--output",
                    str(output),
                ],
                folder,
                timeout=remaining_timeout(
                    started, config["gpu_timeout_seconds"], remaining_rounds=1
                ),
                sample_memory=sample,
            )
            result = read_checkpoint(output) | metrics
            result["max_model_len"] = context
            for log in ("stdout", "stderr"):
                result[log] = (folder / f"{log}.log").read_text(
                    "utf-8", errors="replace"
                )[-200000:]
            atomic_json(final / "result.json", result)
            evidence.commit()
            results.append(result)
            if not metrics["cleaned_up"]:
                break
        return dict(
            contexts=results,
            network_blocked=blocked,
            weights_read_only=read_only,
            snapshot_verified=True,
            evidence_volume="datamate-p2-probe-evidence-v1",
            evidence_key=evidence_key,
            memory_method="sampled total-device nvidia-smi at approximately50ms+command latency; not a physical partition",
            worker_uid=os.getuid(),
            pa_measured=False,
        )

    record_event(
        dict(
            phase="prepared",
            evidence_volume="datamate-p2-probe-evidence-v1",
            evidence_key=key,
        )
    )
    try:
        with modal.enable_output(), app.run():
            record_event(
                dict(phase="app_started", app_id=app.app_id, gpu_image_id=gpu.object_id)
            )
            result = probe.remote(model, cases, key)
            return result | dict(
                app_id=app.app_id,
                gpu_image_id=gpu.object_id,
                base_image=runtime["base_image"],
                billing_usd="not_yet_available",
            )
    except Exception as exc:
        record_event(failure_event(app, "binding_proposals", exc))
        raise
