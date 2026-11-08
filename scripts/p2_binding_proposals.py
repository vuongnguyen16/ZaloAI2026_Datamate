"""Dev-only semantic proposal probe; rebuild before transport, never auto-apply."""

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from datamate.binding_proposals import (
    make_case,
    validate_cached_record,
    validate_cases,
    validate_cloud_result,
)
from datamate.domain_lib.binding_rules import STATUS, header, norm
from datamate.domain_lib.binding_structure import plan_source
from datamate.domain_lib.raw_reader import open_business
from datamate.intent_probe import ContextProbeConfig
from datamate.model_probe import PROFILE, ModelCandidate, preflight
from datamate.prediction_store import regular_bytes

ROOT = Path(__file__).resolve().parents[1]
CONFIG = dict(
    profile=PROFILE,
    workspace=PROFILE,
    budget_usd=30.0,
    estimated_cost_usd=10.0,
    gpu="RTX-PRO-6000",
    memory_budget_bytes=32212254720,
    seed=0,
    max_model_len=4096,
    max_tokens=256,
    gpu_timeout_seconds=900,
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


def registry_model():
    registry = json.loads((ROOT / "manifests/models.json").read_text("utf-8"))
    primary = registry["inference_models"][0]
    return ModelCandidate.model_validate(
        next(
            c
            for c in registry["probe_candidates"]
            if c["repository"] == primary["repository"]
            and c["full_commit_revision"] == primary["full_commit_revision"]
        )
    )


def code_digest():
    files = [
        Path(__file__),
        ROOT / "src/datamate/binding_proposals.py",
        ROOT / "infra/modal_binding_proposals.py",
        ROOT / "infra/p1_runtime/binding_generate.py",
        ROOT / "configs/p1_runtime.json",
        ROOT / "infra/p1_runtime/pyproject.toml",
        ROOT / "infra/p1_runtime/uv.lock",
        ROOT / "src/datamate/model_probe.py",
        ROOT / "src/datamate/probe_diagnostics.py",
        ROOT / "src/datamate/intent_probe.py",
        ROOT / "src/datamate/scoring.py",
        ROOT / "src/datamate/scoped_data.py",
        ROOT / "src/datamate/splits.py",
        ROOT / "src/datamate/prediction_store.py",
        ROOT / "src/datamate/evaluation.py",
        ROOT / "infra/probe_process.py",
        ROOT / "infra/context_probe_process.py",
        ROOT / "infra/modal_model_probe.py",
        ROOT / "scripts/p2_binding_audit.py",
        ROOT / "scripts/p1_probe.py",
        ROOT / "configs/split_policy.json",
    ]
    files += sorted((ROOT / "src/datamate/domain_lib").glob("*.py"))
    return sha(b"".join(p.read_bytes() for p in files))


def excerpt(readme, file):
    match = re.search(
        r"(?m)^#{2,3}\s+Cột trong `" + re.escape(file) + r"`\s*$", readme, re.IGNORECASE
    )
    if not match:
        return ""
    rest = readme[match.start() :]
    end = re.search(r"\n#{1,3}\s", rest)
    return rest[: end.start() if end else len(rest)].strip()


def build_payload(profile_index):
    # Import by sibling module, never a user-provided executable or payload.
    from p2_binding_audit import dev_scope

    from datamate.evaluation import external_metadata

    scope = dev_scope()
    external_metadata(profile_index, scope["source"], scope["split"])
    rulebook_path = scope["source"] / "rulebook.md"
    rulebook = rulebook_path.read_text("utf-8")
    identity = dict(
        code_sha256=code_digest(),
        model_revision=registry_model().full_commit_revision,
        rulebook_sha256=sha(rulebook_path.read_bytes()),
    )
    cases, local, omitted = [], [], []
    for cluster in sorted(set(scope["groups"].values())):
        businesses = sorted(
            (b for b, c in scope["groups"].items() if c == cluster),
            key=lambda b: sha(b.encode()),
        )[:2]
        for bid in businesses:
            with open_business(profile_index, scope["source"], bid) as business:
                plans = [
                    plan_source(t, business.readme) for t in business.schema["tables"]
                ]
                ordered = sorted(
                    plans,
                    key=lambda p: (
                        p.kind != "unresolved",
                        sha(
                            (
                                p.candidate.unit["source_file"]
                                + p.candidate.unit["source_name"]
                            ).encode()
                        ),
                    ),
                )
                if not ordered:
                    continue
                candidate = ordered[0].candidate
                unit = candidate.unit
                columns = [
                    dict(id=c["sql_name"], label=header(c)) for c in unit["columns"]
                ]
                try:
                    case = make_case(
                        "source",
                        excerpt(business.readme, unit["source_file"]),
                        columns,
                        None,
                        identity,
                    )
                    cases.append(case)
                    local.append(
                        dict(
                            case_id=case["id"],
                            business_id=bid,
                            cluster=cluster,
                            kind="source",
                            unit=unit["sql_name"],
                        )
                    )
                except ValueError:
                    omitted.append(
                        dict(business_id=bid, kind="source", reason="projection_budget")
                    )
                status_plans = [
                    p
                    for p in plans
                    if p.kind in {"headers", "combined_lines"}
                    and p.candidate.columns.get("status")
                ]
                if not status_plans:
                    continue
                selected = sorted(
                    status_plans, key=lambda p: p.candidate.unit["sql_name"]
                )[0].candidate
                labels = set()
                iterator = business.iter_rows(selected.unit)
                try:
                    for i, row in enumerate(iterator):
                        if i >= 128:
                            break
                        if row.row >= selected.unit["data_start_row"]:
                            value = (
                                row.cells.get(selected.columns["status"]) or ""
                            ).strip()
                            if value:
                                labels.add(value)
                finally:
                    iterator.close()
                if labels:
                    label = sorted(
                        labels, key=lambda s: (norm(s) in STATUS, sha(s.encode()))
                    )[0]
                    # A contiguous source slice; no fabricated concatenation can pass citation checks.
                    evidence = (
                        rulebook if len(rulebook.encode()) <= 8000 else rulebook[:2500]
                    )
                    case = make_case("status", evidence, [], label, identity)
                    cases.append(case)
                    local.append(
                        dict(
                            case_id=case["id"],
                            business_id=bid,
                            cluster=cluster,
                            kind="status",
                            sampled_rows=128,
                            inventory_complete=False,
                        )
                    )
    # Identical content is analyzed once; membership/provenance never enters cloud cases.
    cases = list({c["id"]: c for c in cases}.values())
    validate_cases(cases)
    return cases, dict(
        partition="dev",
        gold_read=False,
        local_cases=local,
        omitted=omitted,
        source=str(scope["source"].resolve()),
        split=str(scope["split"].resolve()),
        profile_index=str(profile_index.resolve()),
        profile_index_sha256=sha(profile_index.read_bytes()),
    )


def check_output(output, proof):
    from datamate.evaluation import output_path

    output = output_path(output, Path(proof["source"]), Path(proof["split"]))
    profile = Path(proof["profile_index"]).resolve().parent
    if output.resolve().is_relative_to(profile) or profile.is_relative_to(
        output.resolve()
    ):
        raise ValueError("output overlaps profile generation")
    return output


def account():
    import subprocess
    import sys

    from p1_probe import live_account

    result = live_account()
    response = subprocess.run(
        [sys.executable, "-m", "modal", "app", "list", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        timeout=30,
    )
    for row in json.loads(response.stdout):
        keys = {str(k).lower(): v for k, v in row.items()}
        if (
            any(
                name in str(keys.get("description", ""))
                for name in (
                    "datamate-p2-binding-proposals",
                    "datamate-p2-context-probe",
                )
            )
            and keys.get("state") != "stopped"
        ):
            raise ValueError("existing P2 app needs inspection; no automatic retry")
    return result


def cloud_factory():
    import sys

    sys.path.insert(0, str(ROOT))
    from infra.modal_binding_proposals import run_cloud

    return run_cloud


def main(argv=None, *, account_reader=None, transport_factory=None, now=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "check", "run"])
    parser.add_argument("--profile-index", type=Path)
    parser.add_argument("--payload-dir", type=Path)
    parser.add_argument("--billing-json", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.phase == "prepare":
        if not args.profile_index or not args.output:
            parser.error("prepare requires profile-index/output")
        cases, proof = build_payload(args.profile_index)
        check_output(args.output, proof)
        args.output.mkdir(parents=True, exist_ok=False)
        write(args.output / "payload.json", cases)
        write(args.output / "provenance-local.json", proof)
        print(json.dumps(dict(cases=len(cases), gold_read=False)))
        return 0
    if os.environ.get("MODAL_PROFILE") != PROFILE or not args.billing_json:
        raise ValueError("explicit profile and fresh billing required")
    config = ContextProbeConfig.model_validate(CONFIG)
    model = registry_model()
    checked = preflight(
        config,
        model,
        (account_reader or account)(),
        json.loads(args.billing_json.read_text("utf-8-sig")),
        now=now or datetime.now(timezone.utc),
        profile_env=os.environ.get("MODAL_PROFILE"),
    )
    if args.phase == "check":
        print(json.dumps(checked | dict(modal_job_launched=False)))
        return 0
    if not args.payload_dir or not args.output:
        parser.error("run requires payload-dir/output")
    proof = json.loads(
        regular_bytes(args.payload_dir / "provenance-local.json", 1024**2)
    )
    cases = json.loads(regular_bytes(args.payload_dir / "payload.json", 1024**2))
    rebuilt, current = build_payload(Path(proof["profile_index"]))
    if cases != rebuilt or proof != current:
        raise ValueError("payload differs from current authorized dev source")
    check_output(args.output, current)
    args.output.mkdir(parents=True, exist_ok=False)
    write(args.output / "preflight.json", checked)

    def event(value):
        with (args.output / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(value, ensure_ascii=False) + "\n")

    # Cache hits are keyed by the rebuilt content/code/model/rulebook identity.
    cached, pending = {}, []
    validated = []
    cache_dir = args.payload_dir / "cache"
    cache_dir.mkdir(exist_ok=True)
    for case in cases:
        path = cache_dir / (case["id"] + ".json")
        if path.exists():
            record = json.loads(regular_bytes(path, 16384))
            validation = validate_cached_record(record, case)
            validated.append(dict(case_id=case["id"], cached=True, **validation))
            cached[case["id"]] = record
        else:
            pending.append(case)
    result = (
        (transport_factory or cloud_factory)()(
            config.model_dump(), model.model_dump(), pending, event
        )
        if pending
        else dict(contexts=[], cache_only=True)
    )
    write(args.output / "result.json", result)
    outputs = {c["id"]: c for c in cases}
    records = (
        validate_cloud_result(result, pending, config.memory_budget_bytes)
        if pending
        else []
    )
    for record in records:
        validation = validate_cached_record(record, outputs[record["case_id"]])
        validated.append(dict(case_id=record["case_id"], cached=False, **validation))
        # A rejected but completed response is still cached as rejected evidence;
        # it must not cause automatic re-inference of unchanged content.
        path = cache_dir / (record["case_id"] + ".json")
        with path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    write(
        args.output / "validation.json",
        dict(
            records=validated,
            cache_hits=len(cached),
            capabilities_granted=False,
            pa_measured=False,
            billing_usd="not_yet_available",
        ),
    )
    print(
        json.dumps(
            dict(
                output=str(args.output),
                app_id=result.get("app_id"),
                proposals=len(validated),
                cache_hits=len(cached),
                pa_measured=False,
            )
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
