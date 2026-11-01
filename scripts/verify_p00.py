"""Reproduce P00 structural acceptance on the supplied kit, without gold/scoring."""

from pathlib import Path

from datamate.artifacts import new_run, sha256, write_json
from datamate.runner import run_stub
from datamate.validation import inspect_input, inspect_logs, inspect_submission


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    destination = new_run(root / "runs", "p00-contract")
    report = {
        "phase": "P00",
        "scope": "project_structural_acceptance_from_written_spec",
        "run_dir": str(destination.relative_to(root)),
        "splits": {},
        "organizer_scorer_acceptance": "not_applicable_organizer_provides_no_executable",
        "organizer_tool_availability_source": "user_confirmation_2026-11-01",
        "scorer_implementation": "P02_project_scorer_from_written_spec",
        "docker": "deferred_to_P13_by_user",
        "gpu": "not_tested",
        "pa": "not_evaluated",
        "contract_sha256": sha256(root / "manifests/competition_contract.json"),
    }
    for name in ("train", "public_test"):
        split = root / "data" / name
        inputs = inspect_input(split)
        if not inputs["valid"]:
            report["splits"][name] = {"input": inputs}
            report["passed"] = False
            write_json(destination / "verification.json", report)
            print(destination / "verification.json")
            return 1
        run = run_stub(split, destination / name)
        submission = inspect_submission(
            split, run / "submission.jsonl", require_complete=True
        )
        logs = inspect_logs(split, run)
        report["splits"][name] = {
            "input": inputs,
            "submission": submission,
            "logs": logs,
        }
    report["passed"] = all(
        stage["valid"]
        for split in report["splits"].values()
        for stage in split.values()
    )
    write_json(destination / "verification.json", report)
    # Commit only aggregate metadata; full logs and data remain ignored in runs/.
    write_json(root / "reports" / "p00_contract_checks.json", report)
    print(destination / "verification.json")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
