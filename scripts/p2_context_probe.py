"""Guarded dev-only prepare/check/run for P2b; check never constructs transport."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from datamate.intent_probe import ContextProbeConfig, make_case, validate_cases
from datamate.model_probe import PROFILE, ModelCandidate, preflight
from datamate.prediction_store import regular_bytes
from datamate.scoped_data import read_scoped
from datamate.splits import authorize_access, open_split

ROOT = Path(__file__).resolve().parents[1]
CONFIG = dict(
    profile=PROFILE,
    workspace=PROFILE,
    budget_usd=30.0,
    estimated_cost_usd=20.0,
    gpu="RTX-PRO-6000",
    memory_budget_bytes=32212254720,
    seed=0,
    max_model_len=8192,
    max_tokens=256,
    gpu_timeout_seconds=1200,
    startup_timeout_seconds=600,
    staging_timeout_seconds=300,
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def check_apps(entries):
    if not isinstance(entries, list):
        raise ValueError("unexpected app inventory")
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("unexpected app row")
        lowered = {str(k).lower(): v for k, v in entry.items()}
        if (
            "datamate-p2-context-probe" in str(lowered.get("description", ""))
            and lowered.get("state") != "stopped"
        ):
            raise ValueError("existing P2 app requires inspection; do not retry")


def account():
    sys.path.insert(0, str(ROOT / "scripts"))
    from p1_probe import live_account

    result = live_account()
    apps = subprocess.run(
        [sys.executable, "-m", "modal", "app", "list", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=True,
    )
    check_apps(json.loads(apps.stdout))
    return result


def build_payload(profile_index: Path):
    lock = json.loads((ROOT / "manifests/split_lock.json").read_text("utf-8"))
    split = Path(lock["artifact_directory"])
    digest = lock["manifest_sha256"]
    candidate = sha(Path(__file__).read_bytes())
    m, _ = open_split(split, digest, verify_sources=True)
    authorize_access(
        split, digest, "dev", "context", "development", "developer", candidate
    )
    qs, audit = read_scoped(
        split, digest, "dev", "questions", "development", "developer", candidate
    )
    from datamate.evaluation import external_metadata
    from datamate.profile.engine import code_hash

    source = Path(m["source"]["input_dir"])
    external_metadata(profile_index, source, split)
    raw_index = regular_bytes(profile_index, 8 * 1024**2, single_link=True)
    index = json.loads(raw_index)
    if (
        index.get("valid") is not True
        or index.get("profile_code_sha256") != code_hash()
        or index.get("gold_content_read") is not False
    ):
        raise ValueError("current successful no-gold A-T2 profile required")
    entries = {b["business_id"]: b for b in index["businesses"]}
    chosen = []
    for group in sorted(
        (g for g in m["groups"] if g["partition"] == "dev"), key=lambda g: g["group_id"]
    ):
        for business in sorted(group["businesses"], key=lambda b: sha(b.encode()))[:2]:
            records = sorted(
                (q for q in qs.values() if q["business_id"] == business),
                key=lambda q: sha(q["question"].encode()),
            )[:2]
            chosen.extend(records)
    cases, artifacts = [], []
    for business in sorted({q["business_id"] for q in chosen}):
        entry = entries[business]
        if entry.get("valid") is not True:
            raise ValueError("selected business profile invalid")
        loaded = {}
        for kind in ("profile", "schema"):
            path = Path(entry[kind]["path"])
            external_metadata(path, source, split)
            if profile_index.resolve().parent not in path.resolve().parents:
                raise ValueError("descriptor outside profile generation")
            raw = regular_bytes(path, 64 * 1024**2, single_link=True)
            if sha(raw) != entry[kind]["sha256"]:
                raise ValueError("profile artifact hash mismatch")
            loaded[kind] = json.loads(raw)
        profile, schema = loaded["profile"], loaded["schema"]
        if (
            schema["business_id"] != business
            or profile["business_id"] != business
            or schema["ingest_fingerprint"]
            != profile["provenance"]["ingest_fingerprint"]
        ):
            raise ValueError("descriptor business/provenance mismatch")
        for file in profile["provenance"]["files"]:
            expected = m["source"]["files"].get(f"data/{business}/{file['path']}")
            if expected != file["sha256"]:
                raise ValueError("descriptor source differs from frozen source")
        artifacts.append(
            dict(
                business_id=business,
                schema_sha256=entry["schema"]["sha256"],
                profile_sha256=entry["profile"]["sha256"],
            )
        )
        cases.extend(
            make_case(q, schema) for q in chosen if q["business_id"] == business
        )
    validate_cases(cases)
    return cases, dict(
        partition="dev",
        manifest_sha256=digest,
        profile_index=str(profile_index),
        profile_index_sha256=sha(raw_index),
        artifacts=artifacts,
        question_audit=audit,
        candidate_sha256=candidate,
        gold_content_read=False,
    )


def prepare(profile_index: Path, output: Path):
    cases, proof = build_payload(profile_index)
    output.mkdir(parents=True, exist_ok=False)
    write(output / "payload.json", cases)
    write(
        output / "provenance.json",
        proof | {"payload_sha256": sha((output / "payload.json").read_bytes())},
    )
    return {"output": str(output), "cases": len(cases), "gold_content_read": False}


def cloud_factory():
    sys.path.insert(0, str(ROOT))
    from infra.modal_context_probe import run_cloud

    return run_cloud


def main(argv=None, *, account_reader=None, transport_factory=None, now=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "check", "run"))
    parser.add_argument("--profile-index", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--billing-json", type=Path)
    parser.add_argument("--payload-dir", type=Path)
    args = parser.parse_args(argv)
    if args.phase == "prepare":
        if not args.profile_index or not args.output:
            parser.error("prepare requires profile-index/output")
        print(json.dumps(prepare(args.profile_index, args.output)))
        return 0
    if os.environ.get("MODAL_PROFILE") != PROFILE:
        raise ValueError("explicit project profile required")
    if not args.billing_json:
        parser.error("check/run requires billing-json")
    config = ContextProbeConfig.model_validate(CONFIG)
    registry = json.loads((ROOT / "manifests/models.json").read_text("utf-8"))
    primary = registry["inference_models"][0]
    model = ModelCandidate.model_validate(
        next(
            c
            for c in registry["probe_candidates"]
            if c["repository"] == primary["repository"]
            and c["full_commit_revision"] == primary["full_commit_revision"]
        )
    )
    billing = json.loads(args.billing_json.read_text("utf-8-sig"))
    checked = preflight(
        config,
        model,
        (account_reader or account)(),
        billing,
        now=now or datetime.now(timezone.utc),
        profile_env=os.environ.get("MODAL_PROFILE"),
    )
    if args.phase == "check":
        print(json.dumps(checked | {"modal_job_launched": False}))
        return 0
    if not args.payload_dir or not args.output:
        parser.error("run requires payload-dir/output")
    proof = json.loads(regular_bytes(args.payload_dir / "provenance.json", 1024**2))
    payload = regular_bytes(args.payload_dir / "payload.json", 8 * 1024**2)
    lock = json.loads((ROOT / "manifests/split_lock.json").read_text("utf-8"))
    if (
        proof.get("partition") != "dev"
        or proof.get("gold_content_read") is not False
        or proof["manifest_sha256"] != lock["manifest_sha256"]
        or sha(payload) != proof["payload_sha256"]
    ):
        raise ValueError("dev payload provenance mismatch")
    allowed = set(
        authorize_access(
            Path(lock["artifact_directory"]),
            lock["manifest_sha256"],
            "dev",
            "questions",
            "development",
            "developer",
            proof["candidate_sha256"],
        )
    )
    cases = json.loads(payload)
    validate_cases(cases)
    if not {c["id"] for c in cases} <= allowed:
        raise ValueError("payload includes non-dev IDs")
    rebuilt, current_proof = build_payload(Path(proof["profile_index"]))
    if (
        cases != rebuilt
        or proof["profile_index_sha256"] != current_proof["profile_index_sha256"]
        or proof["artifacts"] != current_proof["artifacts"]
    ):
        raise ValueError("payload differs from authorized dev questions/descriptors")
    args.output.mkdir(parents=True, exist_ok=False)
    write(args.output / "preflight.json", checked)
    write(args.output / "payload_provenance.json", proof)

    def event(value):
        with (args.output / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(value, ensure_ascii=False) + "\n")

    result = (transport_factory or cloud_factory)()(
        config.model_dump(), model.model_dump(), cases, event
    )
    write(args.output / "result.json", result)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "app_id": result["app_id"],
                "pa_measured": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
