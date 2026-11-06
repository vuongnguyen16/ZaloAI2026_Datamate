"""Evidence-first orchestration; transport is constructed after CPU preflight."""

import json
from datetime import datetime, timezone
from pathlib import Path

from datamate.artifacts import new_run, sha256, write_json
from datamate.model_probe import ModelCandidate, ProbeConfig, preflight
from datamate.probe_fixtures import build_cases, inference_cases
from datamate.probe_results import evaluate_probe

SOURCE_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATHS = (
    "src/datamate/contracts.py",
    "src/datamate/model_probe.py",
    "src/datamate/probe_fixtures.py",
    "src/datamate/probe_results.py",
    "src/datamate/probe_runner.py",
    "infra/modal_model_probe.py",
    "infra/probe_process.py",
    "infra/p1_runtime/generate.py",
    "infra/p1_runtime/pyproject.toml",
    "infra/p1_runtime/uv.lock",
    "scripts/p1_probe.py",
    "configs/p1_probe.yaml",
    "configs/p1_runtime.json",
    "manifests/models.json",
    "pyproject.toml",
    "uv.lock",
)


def source_inventory() -> dict:
    return {name: sha256(SOURCE_ROOT / name) for name in SOURCE_PATHS}


def execute_probe(
    config: ProbeConfig,
    model: ModelCandidate,
    account: dict,
    billing: dict,
    *,
    profile_env: str | None,
    transport_factory,
    output_root: Path,
    now: datetime | None = None,
) -> Path:
    checked = preflight(
        config,
        model,
        account,
        billing,
        now=now or datetime.now(timezone.utc),
        profile_env=profile_env,
    )
    run = new_run(output_root, "p1-probe")
    write_json(run / "preflight.json", checked)
    write_json(run / "config.json", config.model_dump())
    write_json(run / "model.json", model.model_dump())
    source = source_inventory()
    write_json(run / "source.json", source)
    cases = build_cases()
    write_json(run / "synthetic_cases.json", cases)

    def record_event(event):
        with (run / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    {"at": datetime.now(timezone.utc).isoformat(), **event},
                    allow_nan=False,
                )
                + "\n"
            )

    try:
        result = transport_factory()(
            config.model_dump(),
            model.model_dump(),
            inference_cases(cases),
            record_event,
        )
        write_json(run / "raw_result.json", result)
        report = evaluate_probe(
            cases, result.get("rounds", []), result.get("telemetry", {})
        )
        report["source_changed"] = source_inventory() != source
        if report["source_changed"]:
            report["g1_passed"] = False
            report["errors"].append("source changed during probe")
        report["status"] = "passed" if report["g1_passed"] else "failed"
        write_json(run / "acceptance.json", report)
    except Exception as exc:
        write_json(
            run / "acceptance.json",
            {
                "status": "failed",
                "g1_passed": False,
                "error_type": type(exc).__name__,
                "pa": "not_evaluated",
                "automatic_retries": 0,
            },
        )
        raise
    return run
