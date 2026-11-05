import argparse
import json
import sys
from pathlib import Path

from datamate.ingest import IngestError, LoaderOptions
from datamate.ingest.loader import run_ingest
from datamate.profile import ProfileOptions, run_profile
from datamate.runner import run_smoke, run_stub
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
    ingest.add_argument("--csv-encoding", default="utf-8-sig")
    ingest.add_argument("--csv-delimiter", default=",")
    profile = commands.add_parser(
        "profile", help="Profile raw cache without encoding/header/semantic inference"
    )
    profile.add_argument("--input", type=Path, required=True)
    profile.add_argument("--ingest-report", type=Path, required=True)
    profile.add_argument("--output", type=Path, required=True)
    profile.add_argument("--header-map", type=Path)
    profile.add_argument("--samples", type=int, default=3)
    profile.add_argument("--preview-rows", type=int, default=6)
    profile.add_argument("--value-bytes", type=int, default=256)
    args = parser.parse_args()
    try:
        if args.command == "profile":
            output = run_profile(
                args.input,
                args.ingest_report,
                args.output,
                ProfileOptions(
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
