"""Dev-only CPU binding audit. Real artifacts and review packets stay local."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

from datamate.domain_lib.binding_audit import audit_business
from datamate.domain_lib.binding_diagnostics import (
    METRICS,
    aggregate_patterns,
    attach_repetition,
    diagnose_business,
)
from datamate.evaluation import external_metadata, output_path
from datamate.splits import authorize_access, open_split

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(
            value, handle, ensure_ascii=False, indent=2, default=str, allow_nan=False
        )
        handle.write("\n")


def dev_scope():
    lock = json.loads((ROOT / "manifests/split_lock.json").read_text("utf-8"))
    split = Path(lock["artifact_directory"])
    sha = lock["manifest_sha256"]
    candidate = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    allowed = set(
        authorize_access(
            split, sha, "dev", "context", "development", "developer", candidate
        )
    )
    m, _ = open_split(split, sha, verify_sources=True)
    businesses = {m["source"]["questions"][qid] for qid in allowed}
    expected = {b for b, p in m["business_partitions"].items() if p == "dev"}
    if businesses != expected:
        raise ValueError("dev business authorization mismatch")
    groups = {
        b: f"C{i + 1}"
        for i, g in enumerate(
            sorted(
                (g for g in m["groups"] if g["partition"] == "dev"),
                key=lambda g: g["group_id"],
            )
        )
        for b in g["businesses"]
    }
    return dict(
        source=Path(m["source"]["input_dir"]),
        split=split,
        businesses=businesses,
        groups=groups,
        manifest_sha256=sha,
    )


def main(argv=None, *, scope_reader=None, auditor=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=["audit", "worker", "diagnose", "diagnose-worker"]
    )
    parser.add_argument("--profile-index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--business")
    args = parser.parse_args(argv)
    scope = (scope_reader or dev_scope)()
    if args.business is not None and args.business not in scope["businesses"]:
        raise PermissionError("only authorized dev business allowed")
    if args.mode in {"worker", "diagnose-worker"} and args.business is None:
        parser.error("worker requires business")
    external_metadata(args.profile_index, scope["source"], scope["split"])
    output = output_path(args.output, scope["source"], scope["split"])
    if not args.profile_index.resolve().parent.is_relative_to(
        output.resolve()
    ) and not output.resolve().is_relative_to(args.profile_index.resolve().parent):
        pass
    else:
        raise ValueError("output must be disjoint from profile artifacts")
    output.mkdir(parents=True, exist_ok=False)
    if args.mode in {"worker", "diagnose-worker"}:
        result = (
            auditor
            or (diagnose_business if args.mode == "diagnose-worker" else audit_business)
        )(args.profile_index, scope["source"], args.business)
        write(output / "binding.json", result)
        return 0
    selected = sorted([args.business] if args.business else scope["businesses"])
    results = []
    for bid in selected:
        folder = output / hashlib.sha256(bid.encode()).hexdigest()[:16]
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "diagnose-worker" if args.mode == "diagnose" else "worker",
            "--profile-index",
            str(args.profile_index.resolve()),
            "--business",
            bid,
            "--output",
            str(folder.resolve()),
        ]
        env = os.environ | {
            "OMP_NUM_THREADS": "2",
            "OPENBLAS_NUM_THREADS": "2",
            "PYTHONIOENCODING": "utf-8",
        }
        try:
            run = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
                timeout=90,
            )
            if run.returncode or not (folder / "binding.json").is_file():
                raise ValueError("worker failed")
            result = json.loads((folder / "binding.json").read_text("utf-8"))
        except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
            result = dict(
                business_id=bid,
                count_checked=False,
                revenue_checked=False,
                reason="worker_timeout"
                if isinstance(exc, subprocess.TimeoutExpired)
                else "worker_failed",
                candidates=[],
            )
            folder.mkdir(exist_ok=True)
            write(folder / "binding.json", result)
        result["cluster"] = scope["groups"].get(bid)
        results.append(result)
        print(
            json.dumps(
                dict(
                    business=bid,
                    count_checked=result["count_checked"],
                    revenue_checked=result["revenue_checked"],
                    reason=result.get("reason"),
                ),
                ensure_ascii=False,
            ),
            flush=True,
        )
    summary = dict(
        partition="dev",
        businesses=len(results),
        count_checked=sum(r["count_checked"] for r in results),
        revenue_checked=sum(r["revenue_checked"] for r in results),
        reasons=dict(Counter(r.get("reason") or "checks_passed" for r in results)),
        clusters={
            c: dict(
                businesses=sum(r["cluster"] == c for r in results),
                count_checked=sum(
                    r["count_checked"] and r["cluster"] == c for r in results
                ),
                revenue_checked=sum(
                    r["revenue_checked"] and r["cluster"] == c for r in results
                ),
            )
            for c in sorted(set(scope["groups"].values()))
        },
        gold_read=False,
        pa_measured=False,
        independent_binding_review=False,
        model_called=False,
        review_status="machine checks only; author review and independent/human approval separate",
    )
    summary["mode"] = args.mode
    summary["patterns"] = aggregate_patterns(
        [r | {"sources": r.get("sources", [])} for r in results]
    )
    attach_repetition(results, summary["patterns"])
    summary["blocker_businesses"] = {
        metric: dict(
            Counter(
                reason
                for r in results
                for reason in {
                    b["reason"] for b in r.get("metric_blockers", {}).get(metric, [])
                }
            )
        )
        for metric in METRICS
    }
    write(output / "summary.json", summary)
    write(output / "businesses-local.json", results)
    lines = [
        "# Dev binding review packet — local only",
        "",
        "No gold. Machine checks are not independent oracle approval.",
        "",
    ]
    for result in results:
        lines += [
            f"## {result['business_id']} ({result.get('cluster')})",
            "",
            f"count={result['count_checked']}, revenue={result['revenue_checked']}, reason={result.get('reason')}",
            "",
            "```json",
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            "```",
            "",
        ]
    with (output / "review-packet-local.md").open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        handle.write("\n".join(lines))
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
