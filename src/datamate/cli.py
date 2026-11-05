import argparse
import json
import sys
from pathlib import Path

from datamate.evaluation import run_eval
from datamate.ingest import IngestError, LoaderOptions
from datamate.ingest.loader import run_ingest
from datamate.profile import ProfileOptions, run_profile
from datamate.runner import run_smoke, run_stub
from datamate.splits import (
    authorize_access,
    freeze_split,
    log_public_submission,
    open_split,
)
from datamate.taxonomy import run_taxonomy
from datamate.validation import inspect_input, inspect_logs, inspect_submission


def main() -> int:
    parser = argparse.ArgumentParser(
        description="DataMate CPU harness and structural checks; not a model baseline"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    smoke = commands.add_parser(
        "smoke", help="Run a tiny trusted synthetic fixture with fake responses"
    )
    smoke.add_argument("--config", type=Path, required=True)
    stub = commands.add_parser(
        "stub", help="Format-only abstain output; no real inference"
    )
    stub.add_argument("--input", type=Path, required=True)
    stub.add_argument("--output", type=Path, required=True)
    audit = commands.add_parser(
        "validate-input", help="Split contract checks; never reads gold"
    )
    audit.add_argument("--input", type=Path, required=True)
    validate = commands.add_parser(
        "validate-submission", help="Structural checks only, not scoring"
    )
    validate.add_argument("--input", type=Path, required=True)
    validate.add_argument("--submission", type=Path, required=True)
    validate.add_argument("--require-complete", action="store_true")
    logs = commands.add_parser(
        "validate-logs", help="Check stub/execution log coverage and shape"
    )
    logs.add_argument("--input", type=Path, required=True)
    logs.add_argument("--run", type=Path, required=True)
    ingest = commands.add_parser(
        "ingest", help="Load raw business tables to DuckDB; no cleaning or gold"
    )
    ingest.add_argument("--input", type=Path, required=True)
    ingest.add_argument("--cache", type=Path, required=True)
    ingest.add_argument("--output", type=Path, required=True)
    ingest.add_argument("--business", action="append")
    ingest.add_argument("--csv-encoding", default="auto")
    ingest.add_argument("--csv-delimiter", default="auto")
    ingest.add_argument("--format-map", type=Path)
    profile = commands.add_parser(
        "profile",
        help="Profile raw cache, format evidence and conservative header structure",
    )
    profile.add_argument("--input", type=Path, required=True)
    profile.add_argument("--ingest-report", type=Path, required=True)
    profile.add_argument("--output", type=Path, required=True)
    profile.add_argument("--header-map", type=Path)
    profile.add_argument("--samples", type=int, default=3)
    profile.add_argument("--preview-rows", type=int, default=6)
    profile.add_argument("--value-bytes", type=int, default=256)
    profile.add_argument("--no-auto-header", action="store_true")
    profile.add_argument("--header-scan-rows", type=int, default=64)
    freeze = commands.add_parser(
        "split-freeze", help="Freeze gold-free grouped train split; output stays local"
    )
    freeze.add_argument("--input", type=Path, required=True)
    freeze.add_argument("--structure-labels", type=Path, required=True)
    freeze.add_argument("--labels-sha256", required=True)
    freeze.add_argument(
        "--policy", type=Path, default=Path("configs/split_policy.json")
    )
    freeze.add_argument("--output", type=Path, required=True)
    for name in ("split-check", "split-access", "split-log-public"):
        command = commands.add_parser(
            name, help="Verify/use a hash-pinned local split; never reads gold"
        )
        command.add_argument("--split", type=Path, required=True)
        command.add_argument("--manifest-sha256", required=True)
        if name == "split-access":
            command.add_argument("--partition", required=True)
            command.add_argument("--resource", required=True)
            command.add_argument("--purpose", required=True)
            command.add_argument("--actor", required=True)
            command.add_argument("--candidate-sha256", required=True)
        if name == "split-log-public":
            command.add_argument("--phase", required=True)
            command.add_argument("--purpose", required=True)
            command.add_argument("--candidate-sha256", required=True)
            command.add_argument("--submission-sha256", required=True)
            command.add_argument("--evidence", required=True)
    evaluate = commands.add_parser(
        "run-eval", help="Scoped project scorer; holdout is unavailable in P0"
    )
    evaluate.add_argument("--split", type=Path, required=True)
    evaluate.add_argument("--manifest-sha256", required=True)
    evaluate.add_argument("--partition", choices=("dev", "calibration"), required=True)
    evaluate.add_argument("--submission", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    evaluate.add_argument(
        "--policy", type=Path, default=Path("configs/scoring_policy.json")
    )
    evaluate.add_argument("--control", type=Path)
    evaluate.add_argument("--taxonomy", type=Path)
    evaluate.add_argument("--execution", type=Path)
    evaluate.add_argument("--replicates", type=int, default=1000)
    taxonomy = commands.add_parser(
        "taxonomy", help="Dev-only taxonomy; other partitions stay sealed"
    )
    taxonomy.add_argument("--split", type=Path, required=True)
    taxonomy.add_argument("--manifest-sha256", required=True)
    taxonomy.add_argument(
        "--rules", type=Path, default=Path("configs/taxonomy_rules.json")
    )
    taxonomy.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "run-eval":
            output = run_eval(
                args.split,
                args.manifest_sha256,
                args.partition,
                args.submission,
                args.output,
                args.policy,
                control=args.control,
                taxonomy=args.taxonomy,
                execution=args.execution,
                replicates=args.replicates,
            )
        elif args.command == "taxonomy":
            output = run_taxonomy(
                args.split, args.manifest_sha256, args.rules, args.output
            )
        elif args.command == "split-freeze":
            output = freeze_split(
                args.input,
                args.structure_labels,
                args.labels_sha256,
                args.policy,
                args.output,
            )
        elif args.command == "split-check":
            frozen, _ = open_split(
                args.split, args.manifest_sha256, verify_sources=True
            )
            output = dict(
                valid=True, summary=frozen["summary"], gold_content_read=False
            )
        elif args.command == "split-access":
            ids = authorize_access(
                args.split,
                args.manifest_sha256,
                args.partition,
                args.resource,
                args.purpose,
                args.actor,
                args.candidate_sha256,
            )
            output = dict(
                valid=True,
                authorized_question_ids=ids,
                operation="authorization_only",
                gold_content_read=False,
            )
        elif args.command == "split-log-public":
            log_public_submission(
                args.split,
                args.manifest_sha256,
                args.phase,
                args.purpose,
                args.candidate_sha256,
                args.submission_sha256,
                args.evidence,
            )
            output = dict(valid=True, operation="audit_only; no submission sent")
        elif args.command == "profile":
            output = run_profile(
                args.input,
                args.ingest_report,
                args.output,
                ProfileOptions(
                    detect_headers=not args.no_auto_header,
                    header_scan_rows=args.header_scan_rows,
                    samples_per_column=args.samples,
                    preview_rows=args.preview_rows,
                    value_bytes=args.value_bytes,
                ),
                args.header_map,
            )
        elif args.command == "ingest":
            output = run_ingest(
                args.input,
                args.cache,
                args.output,
                LoaderOptions(
                    csv_encoding=args.csv_encoding, csv_delimiter=args.csv_delimiter
                ),
                args.business,
                args.format_map,
            )
        elif args.command == "validate-input":
            output = inspect_input(args.input)
        elif args.command == "validate-submission":
            output = inspect_submission(
                args.input, args.submission, require_complete=args.require_complete
            )
        elif args.command == "validate-logs":
            output = inspect_logs(args.input, args.run)
        elif args.command == "smoke":
            output = run_smoke(args.config)
        else:
            output = run_stub(args.input, args.output)
    except IngestError as exc:
        print(
            json.dumps(
                {"valid": False, "errors": [exc.record()]}, ensure_ascii=False, indent=2
            )
        )
        return 2
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(output, ensure_ascii=False, indent=2)
        if isinstance(output, dict)
        else output
    )
    return 0 if not isinstance(output, dict) or output["valid"] else 2
