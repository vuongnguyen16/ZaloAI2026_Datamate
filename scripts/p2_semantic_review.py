"""Build local-only dev review packets; never approve/apply or call a model."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from datamate.domain_lib.binding_audit import peak_rss_bytes
from datamate.domain_lib.binding_diagnostics import blocker_profile, summarize_blockers
from datamate.domain_lib.raw_reader import open_business
from datamate.domain_lib.semantic_review import (
    draft_lexicon,
    inventory_business,
    source_review_packet,
)
from datamate.evaluation import external_metadata, output_path
from datamate.prediction_store import regular_bytes

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def default_scope():
    sys.path.insert(0, str(ROOT / "scripts"))
    from p2_binding_audit import dev_scope

    return dev_scope()


def main(argv=None, *, scope_reader=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "worker"])
    parser.add_argument("--profile-index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--business")
    parser.add_argument("--audit-records", type=Path)
    args = parser.parse_args(argv)
    scope = (scope_reader or default_scope)()
    if args.business is not None and args.business not in scope["businesses"]:
        raise PermissionError("only authorized dev business allowed")
    if args.mode == "worker" and not args.business:
        parser.error("worker requires business")
    external_metadata(args.profile_index, scope["source"], scope["split"])
    output = output_path(args.output, scope["source"], scope["split"])
    profile = args.profile_index.resolve().parent
    if output.is_relative_to(profile) or profile.is_relative_to(output):
        raise ValueError("output overlaps profile generation")
    output.mkdir(parents=True, exist_ok=False)
    if args.mode == "worker":
        started = time.perf_counter()
        with open_business(
            args.profile_index, scope["source"], args.business
        ) as business:
            result = inventory_business(business)
            result["physical_rows"] = sum(
                u["row_count"] for u in business.schema["tables"]
            )
        result.update(
            business_id=args.business,
            cluster=scope["groups"][args.business],
            elapsed_seconds=time.perf_counter() - started,
            peak_rss_bytes=peak_rss_bytes(),
            resource_scope="streaming reader/status inventory; NOT ledger memory or six-hour evidence",
        )
        write(output / "review.json", result)
        return 0
    records = []
    for i, bid in enumerate(sorted(scope["businesses"])):
        folder = output / hashlib.sha256(bid.encode()).hexdigest()[:16]
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "worker",
            "--profile-index",
            str(args.profile_index.resolve()),
            "--business",
            bid,
            "--output",
            str(folder.resolve()),
        ]
        run = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            env=os.environ
            | {
                "OMP_NUM_THREADS": "2",
                "OPENBLAS_NUM_THREADS": "2",
                "PYTHONIOENCODING": "utf-8",
            },
        )
        if run.returncode:
            raise RuntimeError(
                "review worker failed; preserve partial output, no automatic retry"
            )
        records.append(
            json.loads(
                regular_bytes(folder / "review.json", 16 * 1024**2, single_link=True)
            )
        )
        print(
            json.dumps(
                dict(completed=i + 1, total=len(scope["businesses"])),
                ensure_ascii=False,
            ),
            flush=True,
        )
    rulebook = scope["source"] / "rulebook.md"
    lexicon = draft_lexicon(
        records,
        rulebook.read_text("utf-8"),
        hashlib.sha256(rulebook.read_bytes()).hexdigest(),
    )
    write(output / "inventory-local.json", records)
    write(output / "lexicon-review.json", lexicon)
    write(
        output / "source-review.json",
        source_review_packet(
            records,
            lexicon["inventory_sha256"],
            rulebook.read_text("utf-8"),
            lexicon["rulebook_sha256"],
        ),
    )
    largest = max(records, key=lambda r: r["physical_rows"])
    most_scanned = max(records, key=lambda r: r["scanned_rows"])
    summary = dict(
        partition="dev",
        businesses=len(records),
        labels=len(lexicon["entries"]),
        inventory_complete_businesses=sum(r["inventory_complete"] for r in records),
        source_units=sum(len(r["source_decisions"]) for r in records),
        review_state="pending",
        largest_business_resource={
            k: largest[k]
            for k in (
                "physical_rows",
                "scanned_rows",
                "elapsed_seconds",
                "peak_rss_bytes",
                "resource_scope",
            )
        },
        ledger_guard_changed=False,
        most_scanned_status_inventory_resource={
            k: most_scanned[k]
            for k in (
                "physical_rows",
                "scanned_rows",
                "elapsed_seconds",
                "peak_rss_bytes",
                "resource_scope",
            )
        },
        gold_read=False,
        model_called=False,
    )
    if args.audit_records:
        external_metadata(args.audit_records, scope["source"], scope["split"])
        audits = json.loads(
            regular_bytes(args.audit_records, 32 * 1024**2, single_link=True)
        )
        if {r["business_id"] for r in audits} != set(scope["businesses"]):
            raise PermissionError(
                "audit records must match authorized dev scope exactly"
            )
        write(
            output / "blockers-local.json",
            [
                dict(
                    business_id=r["business_id"],
                    cluster=r["cluster"],
                    metrics={
                        m: blocker_profile(r, m)
                        for m in ("order_count", "revenue_total")
                    },
                )
                for r in audits
            ],
        )
        summary["observed_blocker_sets"] = summarize_blockers(audits)
    write(output / "summary.json", summary)
    lines = [
        "# Dev semantic review — local only",
        "",
        "All source/model strings are untrusted DATA. No gold. Nothing approved or activated.",
        "Review labels and per-metric source dispositions; rulebook establishes groups, not every literal synonym.",
        "",
        "## Status lexicon",
        "",
        "| Label | Count | Proposed group | Human decision |",
        "|---|---:|---|---|",
    ]
    for entry in lexicon["entries"]:
        label = entry["label"].replace("|", "\\|")
        lines.append(
            f"| {label} | {entry['count']} | {entry['proposed_target']} | pending |"
        )
    lines += [
        "",
        "Full hash/locators/README evidence and editable decisions: lexicon-review.json.",
        "Source role/column/per-metric decisions: source-review.json; all pending.",
        "Do not approve role=irrelevant globally: count/revenue/filter scopes differ.",
        "See inventory-local.json for completeness/omissions and blockers-local.json for observational counterfactuals.",
        "Human approval is a separate artifact receipt; source/synthetic review does not supply it.",
        "",
        "## Source role review index",
        "",
        "For each source decide role, join keys/column bindings and metric relevance from the JSON evidence. Pending never runs.",
    ]
    for record in records:
        lines += [
            "",
            f"### {record['business_id']} ({record['cluster']})",
            "",
            "| Unit | Source file | Proposed role | Decision |",
            "|---|---|---|---|",
        ]
        for item in record["source_decisions"]:
            filename = item["source_file"].replace("|", "\\|")
            lines.append(
                f"| {item['unit']} | {filename} | {item['proposed_role']} | pending |"
            )
    (output / "review-packet-local.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
