import argparse
import json
import sys
from pathlib import Path

from datamate.runner import run_smoke, run_stub
from datamate.validation import inspect_input, inspect_logs, inspect_submission


def main() -> int:
    parser = argparse.ArgumentParser(
        description="DataMate CPU harness and P00 structural checks; not B0"
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
        "validate-input", help="P00 split contract checks; never reads gold"
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
    args = parser.parse_args()
    try:
        if args.command == "validate-input":
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
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(output, ensure_ascii=False, indent=2)
        if isinstance(output, dict)
        else output
    )
    return 0 if not isinstance(output, dict) or output["valid"] else 2
