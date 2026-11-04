"""Structural checks from the supplied contract, never answer matching/PA.

This module reads questions, file metadata, rule/calendar hashes and predictions.
It does not open gold labels or inspect business table content.
"""

import csv
import math
from collections import Counter
from pathlib import Path

from datamate.artifacts import sha256
from datamate.contracts import Submission, json_object
from datamate.runner import read_questions

VALIDATION_SCOPE = "project_structure_from_spec; not_organizer_evaluator"


def inspect_input(input_dir: Path) -> dict:
    directory = input_dir.resolve(strict=True)
    errors, warnings = [], []
    required = ("questions.jsonl", "rulebook.md", "calendar.csv")
    hashes = {}
    for name in required:
        path = directory / name
        if not path.is_file():
            errors.append(f"missing required file: {name}")
        elif not path.resolve().is_relative_to(directory):
            errors.append(f"input file points outside split: {name}")
        elif path.stat().st_size == 0:
            errors.append(f"required file is empty: {name}")
        else:
            hashes[name] = sha256(path)
    report = {
        "scope": VALIDATION_SCOPE,
        "input_dir": str(directory),
        "errors": errors,
        "warnings": warnings,
        "input_sha256": hashes,
        "gold_file_present": (directory / "answers.jsonl").is_file(),
        "gold_content_read": False,
    }
    if errors:
        return {**report, "valid": False}
    try:
        questions = read_questions(directory / "questions.jsonl", limit=10000)
    except ValueError as exc:
        return {**report, "valid": False, "errors": [str(exc)]}
    business_root = directory / "data"
    referenced = {q.business_id for q in questions}
    data_formats = Counter()
    for business_id in sorted(referenced):
        path = business_root / business_id
        # Treat the business reference as a single directory name on Windows/Linux.
        if business_id in (".", "..") or any(
            c in business_id for c in ("/", "\\", ":")
        ):
            errors.append(f"invalid business directory reference: {business_id}")
            continue
        if not path.is_dir() or not path.resolve().is_relative_to(directory):
            errors.append(f"missing/outside business directory: {business_id}")
            continue
        readme = path / "README.md"
        if not readme.is_file():
            errors.append(f"missing business README: {business_id}")
        elif not readme.stat().st_size:
            warnings.append(
                f"empty README allowed but context is limited: {business_id}"
            )
        table_files = [
            p
            for p in path.iterdir()
            if p.is_file()
            and p.suffix.lower()
            in (
                ".csv",
                ".xlsx",
                ".sqlite",
            )
        ]
        if not table_files:
            errors.append(
                f"no supported table file in business directory: {business_id}"
            )
        for table in table_files:
            if not table.resolve().is_relative_to(directory):
                errors.append(f"table points outside split: {business_id}/{table.name}")
            data_formats[table.suffix.lower()] += 1
    with (directory / "calendar.csv").open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        calendar_rows = 0
        if not header or len(set(header)) != len(header) or any(not x for x in header):
            errors.append("calendar header must have nonempty unique columns")
        for index, row in enumerate(reader, 2):
            calendar_rows += 1
            if len(row) != len(header):
                errors.append(f"calendar column count mismatch at line {index}")
    return {
        **report,
        "valid": not errors,
        "questions": len(questions),
        "question_fields": sorted(questions[0].model_fields_set),
        "referenced_businesses": len(referenced),
        "table_formats": dict(data_formats),
        "calendar_columns": header,
        "calendar_rows": calendar_rows,
    }


def inspect_submission(
    input_dir: Path, submission_path: Path, *, require_complete: bool = False
) -> dict:
    questions = read_questions(
        input_dir.resolve(strict=True) / "questions.jsonl", limit=10000
    )
    expected = {q.id for q in questions}
    seen, counts, errors = set(), Counter(), []
    with submission_path.open(encoding="utf-8-sig") as handle:
        for index, line in enumerate(handle, 1):
            try:
                entry = Submission.model_validate(json_object(line))
            except ValueError as exc:
                errors.append(f"invalid submission at line {index}: {exc}")
                continue
            if entry.id in seen:
                errors.append(f"duplicate submission id at line {index}: {entry.id}")
            if entry.id not in expected:
                errors.append(f"unknown submission id at line {index}: {entry.id}")
            seen.add(entry.id)
            counts[entry.type] += 1
    missing = expected - seen
    if missing and require_complete:
        errors.append(f"missing {len(missing)} question IDs (require_complete policy)")
    return {
        "scope": VALIDATION_SCOPE,
        "valid": not errors,
        "errors": errors,
        "input_questions": len(expected),
        "submitted_unique_ids": len(seen),
        "missing_ids_counted_as_abstain": len(missing),
        "types": dict(counts),
        "require_complete": require_complete,
        "submission_sha256": sha256(submission_path),
        "scorer_acceptance": "not_applicable_organizer_provides_no_executable",
        "pa": "not_evaluated",
    }


def inspect_logs(input_dir: Path, run_dir: Path) -> dict:
    """Check generated run logs against predictions, not private reasoning traces."""
    expected = {
        q.id for q in read_questions(input_dir / "questions.jsonl", limit=10000)
    }
    errors, seen = [], set()
    submission_path = run_dir / "submission.jsonl"
    submission_check = inspect_submission(
        input_dir, submission_path, require_complete=True
    )
    errors.extend(submission_check["errors"])
    predictions = {}
    with submission_path.open(encoding="utf-8-sig") as handle:
        for line in handle:
            try:
                prediction = Submission.model_validate(json_object(line))
                predictions[prediction.id] = prediction.output()
            except ValueError:
                pass  # Already reported by inspect_submission above.
    for path in sorted((run_dir / "logs").glob("*.json")):
        try:
            entry = json_object(path.read_text("utf-8-sig"))
            identifier = entry["question_id"]
            if (
                not isinstance(identifier, str)
                or identifier not in expected
                or identifier in seen
            ):
                raise ValueError("duplicate or unknown question_id")
            seen.add(identifier)
            prediction = Submission.model_validate(entry["answer"])
            if prediction.id != identifier:
                raise ValueError("log answer id differs from question_id")
            if prediction.output() != predictions.get(identifier):
                raise ValueError("logged answer differs from submission")
            duration = entry["duration_seconds"]
            if (
                type(duration) not in (int, float)
                or not math.isfinite(duration)
                or duration < 0
            ):
                raise ValueError("invalid duration")
            if not entry.get("evidence") and not entry.get("sql"):
                raise ValueError(
                    "missing execution evidence or explicit stub explanation"
                )
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f"invalid log {path.name}: {exc}")
    if expected - seen:
        errors.append(f"missing logs for {len(expected - seen)} questions")
    return {
        "valid": not errors,
        "errors": errors,
        "question_logs": len(seen),
        "scope": VALIDATION_SCOPE,
    }
