import argparse
import sys
from pathlib import Path

from datamate.runner import run_smoke, run_stub


def main() -> int:
    parser = argparse.ArgumentParser(description="DataMate S00 CPU harness; not B0")
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
    args = parser.parse_args()
    try:
        output = (
            run_smoke(args.config)
            if args.command == "smoke"
            else run_stub(args.input, args.output)
        )
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(output)
    return 0
