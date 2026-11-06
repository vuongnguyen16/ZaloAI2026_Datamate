"""Guarded P1 entrypoint. `check` is read-only; `run` launches the approved probe."""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from datamate.model_probe import PROFILE, ModelCandidate, ProbeConfig, preflight
from datamate.probe_runner import execute_probe

ROOT = Path(__file__).resolve().parents[1]


def live_account() -> dict:
    env = {**os.environ, "MODAL_PROFILE": PROFILE, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        [sys.executable, "-m", "modal", "token", "info"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=30,
    )
    if result.returncode:
        raise ValueError("Modal live account verification failed; no job launched")
    account = {}
    for name in ("Workspace", "User"):
        match = re.search(rf"^{name}:\s*(\S+)", result.stdout, re.MULTILINE)
        account[name.lower()] = match.group(1) if match else None
    apps = subprocess.run(
        [sys.executable, "-m", "modal", "app", "list", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=30,
    )
    if apps.returncode:
        raise ValueError("Cannot verify active Modal apps; no job launched")
    entries = json.loads(apps.stdout)
    if not isinstance(entries, list):
        raise ValueError("Unexpected Modal app inventory; no job launched")
    for entry in entries:
        if (
            "datamate-p1-model-probe" in str(entry)
            and "stopped" not in str(entry).lower()
        ):
            raise ValueError(
                "An existing P1 app requires inspection before another launch"
            )
    account["conflicting_p1_apps"] = 0
    return account


def cloud_factory():
    sys.path.insert(0, str(ROOT))
    from infra.modal_model_probe import run_cloud

    return run_cloud


def main(argv=None, *, account_reader=None, transport_factory=None, now=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("check", "run"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--billing-json", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/p1_probe.yaml")
    parser.add_argument("--output-root", type=Path, default=ROOT / "runs")
    args = parser.parse_args(argv)
    if os.environ.get("MODAL_PROFILE") != PROFILE:
        raise ValueError("set explicit project profile before any account access")
    config = ProbeConfig.model_validate(yaml.safe_load(args.config.read_text("utf-8")))
    registry = json.loads((ROOT / "manifests/models.json").read_text("utf-8"))
    candidates = [
        entry
        for entry in registry["probe_candidates"]
        if entry["repository"] == args.model
    ]
    if len(candidates) != 1:
        raise ValueError("model must be an eligible registered P1 candidate")
    model = ModelCandidate.model_validate(candidates[0])
    billing = json.loads(args.billing_json.read_text("utf-8-sig"))
    account = (account_reader or live_account)()
    current = now or datetime.now(timezone.utc)
    checked = preflight(
        config,
        model,
        account,
        billing,
        now=current,
        profile_env=os.environ.get("MODAL_PROFILE"),
    )
    if args.phase == "check":
        print(json.dumps({**checked, "modal_job_launched": False}, ensure_ascii=False))
        return 0
    run = execute_probe(
        config,
        model,
        account,
        billing,
        profile_env=os.environ.get("MODAL_PROFILE"),
        transport_factory=transport_factory or cloud_factory,
        output_root=args.output_root,
        now=current,
    )
    report = json.loads((run / "acceptance.json").read_text("utf-8"))
    print(json.dumps({"run": str(run), "g1_passed": report["g1_passed"]}))
    return 0 if report["g1_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
