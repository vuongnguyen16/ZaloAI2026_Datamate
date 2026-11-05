"""Repository context and source evidence. Never opens the competition kit."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TIMELINE = "Research/Timeline DataMate theo nhóm việc A–G.docx"
SOURCE_DIRS = (
    "src",
    "scripts",
    "tests",
    "infra",
    "configs",
    ".agents",
    ".github",
    "Research/timeline_assets",
)
SOURCE_FILES = (
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    ".gitignore",
    "predict.sh",
    "manifests/competition_contract.json",
    "manifests/contract_sources.json",
    "manifests/models.json",
    "manifests/timeline_source.json",
    "tasks/backlog.json",
    "Research/Timeline_DataMate_A-G.md",
    TIMELINE,
)
READ_FIRST = (
    "AGENTS.md",
    "README.md",
    "docs/project_state.md",
    "tasks/backlog.json",
    "docs/requirements.md",
    "manifests/competition_contract.json",
    "docs/harness.md",
    "manifests/timeline_source.json",
)


def git_value(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def source_snapshot(root: Path) -> dict:
    """Hash only code/config/test inputs, including untracked files, without diff."""
    root = root.resolve()
    paths = [root / name for name in SOURCE_FILES if (root / name).is_file()]
    for directory in SOURCE_DIRS:
        paths.extend(
            path
            for path in (root / directory).rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix not in (".pyc", ".pyo")
        )
    hashes = {}
    for path in sorted(paths):
        resolved = path.resolve()
        allowed = resolved in {root / name for name in SOURCE_FILES} or any(
            resolved.is_relative_to(root / directory) for directory in SOURCE_DIRS
        )
        if not resolved.is_relative_to(root) or not allowed:
            raise ValueError(f"source path escapes allowlist: {path.relative_to(root)}")
        with path.open("rb") as handle:
            hashes[path.relative_to(root).as_posix()] = hashlib.file_digest(
                handle, "sha256"
            ).hexdigest()
    return {
        "files": hashes,
        "fingerprint": hashlib.sha256(
            json.dumps(hashes, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }


def timeline_reference(root: Path) -> dict:
    path = root / TIMELINE
    if not path.is_file():
        return {"status": "missing", "path": TIMELINE}
    with path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    return {
        "status": "working_tree",
        "path": TIMELINE,
        "sha256": digest,
    }


def latest_cpu(root: Path, fingerprint: str) -> dict:
    records = sorted(
        (root / "runs").glob("cpu-check-*/gate.json"),
        key=lambda p: p.stat().st_mtime_ns,
        reverse=True,
    )
    if not records:
        return {"status": "not_recorded", "freshness": "unknown"}
    path = records[0]
    try:
        record = json.loads(path.read_text("utf-8"))
        if not isinstance(record, dict):
            raise ValueError("gate record must be an object")
    except (OSError, ValueError):
        return {"status": "invalid_record", "path": path.relative_to(root).as_posix()}
    return {
        "status": record.get("status", "unknown"),
        "path": path.relative_to(root).as_posix(),
        "freshness": "current"
        if record.get("source_fingerprint") == fingerprint
        else "stale",
    }


def planning_errors(root: Path, tasks: list[dict], timeline: dict) -> list[str]:
    """Fail closed on stale planning provenance and malformed task graphs."""
    errors = []
    registry_path = root / "manifests/timeline_source.json"
    try:
        registry = json.loads(registry_path.read_text("utf-8"))
        files = registry["files"]
        required = {TIMELINE, "Research/Timeline_DataMate_A-G.md"}
        if registry.get("schema_version") != 1 or not required <= files.keys():
            raise ValueError("invalid timeline registry schema")
        for name, expected in files.items():
            path = (root / name).resolve()
            allowed = name in required or name.startswith("Research/timeline_assets/")
            if not allowed or not path.is_relative_to(root.resolve()):
                raise ValueError("timeline registry path escapes allowlist")
            if (
                not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != expected
            ):
                errors.append(f"Timeline file missing or stale: {name}")
        if files[TIMELINE] != timeline.get("sha256"):
            errors.append("Timeline DOCX differs from the synchronized source")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        errors.append(f"Timeline synchronization registry missing or invalid: {exc}")

    by_id = {t["id"]: t for t in tasks}
    if len(by_id) != len(tasks):
        errors.append("Duplicate task IDs")
    visiting, visited = set(), set()

    def visit(id):
        if id in visiting:
            errors.append(f"Dependency cycle: {id}")
            return
        if id in visited:
            return
        visiting.add(id)
        for dep in by_id[id].get("depends_on", []):
            if dep not in by_id:
                errors.append(f"Unknown dependency {dep} in {id}")
            else:
                visit(dep)
        visiting.remove(id)
        visited.add(id)

    for id, task in by_id.items():
        visit(id)
        if task.get("source") != TIMELINE or task.get("source_sha256") != timeline.get(
            "sha256"
        ):
            errors.append(f"Task {id} is not synchronized to the current DOCX")
        if task.get("status") not in {
            "todo",
            "in_progress",
            "done",
            "done_with_limitations",
            "skipped",
        }:
            errors.append(f"Invalid task status: {id}")
        if task.get("status") == "skipped" and not (
            task.get("optional") and task.get("skip_reason", "").strip()
        ):
            errors.append(f"Skipped task needs optional=true and skip_reason: {id}")
        if task.get("status") in {"in_progress", "done", "done_with_limitations"}:
            unmet = [
                d
                for d in task.get("depends_on", [])
                if not resolved_task(by_id.get(d, {}))
            ]
            if unmet:
                errors.append(
                    f"Started/completed task {id} has unmet dependencies: {', '.join(unmet)}"
                )
    if sum(t.get("status") == "in_progress" for t in tasks) > 1:
        errors.append("Only one task may be in_progress")
    timeline["sync_status"] = "current" if not errors else "blocked"
    return errors


def resolved_task(task: dict) -> bool:
    return task.get("status") in {"done", "done_with_limitations"} or (
        task.get("status") == "skipped"
        and task.get("optional") is True
        and bool(task.get("skip_reason", "").strip())
    )


def build_context(root: Path, task_id: str | None = None) -> dict:
    tasks = json.loads((root / "tasks/backlog.json").read_text("utf-8"))
    by_id = {task["id"]: task for task in tasks}
    if len(by_id) != len(tasks):
        raise ValueError("duplicate task IDs in backlog")
    if task_id is not None and task_id not in by_id:
        raise ValueError(f"unknown task ID: {task_id}")
    task = by_id[task_id] if task_id else None
    unmet = [
        dependency
        for dependency in (task or {}).get("depends_on", [])
        if not resolved_task(by_id.get(dependency, {}))
    ]
    timeline = timeline_reference(root)
    errors = planning_errors(root, tasks, timeline)
    other_active = [
        t["id"] for t in tasks if t["status"] == "in_progress" and t["id"] != task_id
    ]
    warnings = []
    if timeline["status"] != "working_tree":
        warnings.append(
            "Timeline missing; supply the current A–G timeline before planning. Superseded plans are not used."
        )
    missing = [name for name in READ_FIRST if not (root / name).is_file()]
    if missing:
        warnings.append(f"Missing context files: {', '.join(missing)}")
    warnings.extend(errors)
    state_path = root / "docs/project_state.md"
    return {
        "schema_version": 3,
        "read_first": list(READ_FIRST),
        "project_state": state_path.read_text("utf-8")
        if state_path.is_file()
        else None,
        "timeline": timeline,
        "task": task,
        "active_tasks": [t for t in tasks if t["status"] == "in_progress"],
        "dependency_status": "blocked"
        if unmet or errors or (task and other_active)
        else "ready"
        if task
        else "not_selected",
        "unmet_dependencies": unmet,
        "other_active_tasks": other_active,
        "planning_errors": errors,
        "latest_cpu": latest_cpu(root, source_snapshot(root)["fingerprint"]),
        "gpu": "not_tested_by_context_command",
        "pa": "not_evaluated_by_context_command",
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    context = subparsers.add_parser(
        "context", help="read state/task/dependencies; no jobs"
    )
    context.add_argument("--task")
    args = parser.parse_args()
    try:
        result = build_context(ROOT, args.task)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"context error: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
