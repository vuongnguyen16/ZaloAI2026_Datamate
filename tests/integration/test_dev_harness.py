"""Exercise the developer gate in isolated, synthetic workspaces."""

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_harness():
    spec = importlib.util.spec_from_file_location(
        "datamate_dev_harness", ROOT / "scripts/harness.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synchronize_fixture(root, tasks):
    """Give synthetic plans the same provenance contract as real plans."""
    harness = load_harness()
    timeline = root / harness.TIMELINE
    timeline.parent.mkdir(exist_ok=True)
    if not timeline.exists():
        timeline.write_bytes(b"synthetic timeline")
    web = root / "Research/Timeline_DataMate_A-G.md"
    web.write_text("synthetic reading copy", encoding="utf-8")
    hashes = {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (timeline, web)
    }
    (root / "manifests").mkdir(exist_ok=True)
    (root / "manifests/timeline_source.json").write_text(
        json.dumps({"schema_version": 1, "files": hashes}), encoding="utf-8"
    )
    for task in tasks:
        task.update(source=harness.TIMELINE, source_sha256=hashes[harness.TIMELINE])
    (root / "tasks").mkdir(exist_ok=True)
    (root / "tasks/backlog.json").write_text(json.dumps(tasks), encoding="utf-8")


def gate_workspace(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("check.py", "harness.py"):
        shutil.copy2(ROOT / "scripts" / name, scripts / name)
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
        'markers = ["gpu: remote GPU", "modal: remote Modal"]\n',
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    return tmp_path


def run_gate(root):
    result = subprocess.run(
        [sys.executable, str(root / "scripts/check.py")],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    reports = sorted((root / "runs").glob("cpu-check-*/gate.json"))
    assert reports, result.stdout + result.stderr
    return result, json.loads(reports[-1].read_text("utf-8"))


def test_gate_records_real_failure_then_success_and_excludes_cloud(tmp_path):
    root = gate_workspace(tmp_path)
    test = root / "tests/test_synthetic.py"
    test.write_text(
        "import pytest\n\n\ndef test_cpu():\n    assert False\n\n\n"
        "@pytest.mark.gpu\ndef test_gpu():\n    assert False\n\n\n"
        "@pytest.mark.modal\ndef test_modal_cpu():\n    assert False\n",
        encoding="utf-8",
    )
    failed, red = run_gate(root)
    assert failed.returncode == 1
    assert red["status"] == "failed"
    assert red["stages"][-1]["name"] == "pytest"
    assert red["stages"][-1]["exit_code"] == 1
    log = root / red["stages"][-1]["log"]
    assert "1 failed, 2 deselected" in log.read_text("utf-8")
    assert red["gpu"] == "not_tested"
    assert red["pa"] == "not_evaluated"

    test.write_text(
        test.read_text("utf-8").replace(
            "def test_cpu():\n    assert False", "def test_cpu():\n    assert True"
        ),
        encoding="utf-8",
    )
    passed, green = run_gate(root)
    assert passed.returncode == 0, passed.stdout + passed.stderr
    assert green["status"] == "passed"
    assert len(green["stages"]) == 3
    assert all(s["exit_code"] == 0 for s in green["stages"])
    assert red["source_fingerprint"] != green["source_fingerprint"]
    assert green["modal_model"] == "not_tested"
    assert green["pa"] == "not_evaluated"


def test_empty_collection_is_a_failed_gate(tmp_path):
    result, report = run_gate(gate_workspace(tmp_path))
    assert result.returncode == 5
    assert report["status"] == "failed"
    assert report["stages"][-1]["exit_code"] == 5


def test_lint_failure_stops_before_pytest(tmp_path):
    root = gate_workspace(tmp_path)
    (root / "tests/test_unused.py").write_text("import math\n", encoding="utf-8")
    result, report = run_gate(root)
    assert result.returncode != 0
    assert report["status"] == "failed"
    assert [s["name"] for s in report["stages"]] == ["ruff_check"]
    assert not list((root / "runs").glob("cpu-check-*/pytest.log"))


def test_gate_refuses_pass_if_source_changes_during_tests(tmp_path):
    root = gate_workspace(tmp_path)
    (root / "tests/test_mutation.py").write_text(
        "from pathlib import Path\n\n\ndef test_cpu():\n"
        '    Path("src").mkdir()\n'
        '    Path("src/new.py").write_text("# mutation\\n")\n',
        encoding="utf-8",
    )
    result, report = run_gate(root)
    assert result.returncode == 1
    assert all(s["status"] == "passed" for s in report["stages"])
    assert report["source_changed_during_gate"] is True
    assert report["status"] == "failed"


def test_snapshot_detects_untracked_test_changes_without_reading_kit(tmp_path):
    harness = load_harness()
    (tmp_path / "tests").mkdir()
    test = tmp_path / "tests/test_new.py"
    test.write_text("assert True\n", encoding="utf-8")
    first = harness.source_snapshot(tmp_path)
    # Deliberately outside the source allowlist; never source evidence.
    (tmp_path / "private_fixture").mkdir()
    (tmp_path / "private_fixture/answers.jsonl").write_text("secret synthetic")
    assert harness.source_snapshot(tmp_path) == first
    test.write_text("assert False\n", encoding="utf-8")
    assert harness.source_snapshot(tmp_path) != first


def test_context_resolves_timeline_and_group_dependencies(tmp_path):
    harness = load_harness()
    (tmp_path / "tasks").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/project_state.md").write_text("A-T1 active", encoding="utf-8")
    timeline = tmp_path / harness.TIMELINE
    timeline.parent.mkdir()
    timeline.write_bytes(b"synthetic timeline document")
    tasks = [
        {"id": "G-FOUNDATION", "status": "done_with_limitations"},
        {"id": "A-T1", "status": "in_progress", "depends_on": ["G-FOUNDATION"]},
        {"id": "D-E-T2", "status": "todo", "depends_on": ["A-T1"]},
    ]
    synchronize_fixture(tmp_path, tasks)
    current = harness.build_context(tmp_path, "A-T1")
    assert current["task"]["id"] == "A-T1"
    assert current["dependency_status"] == "ready"
    assert current["timeline"]["status"] == "working_tree"
    assert len(current["timeline"]["sha256"]) == 64
    future = harness.build_context(tmp_path, "D-E-T2")
    assert future["dependency_status"] == "blocked"
    assert future["unmet_dependencies"] == ["A-T1"]
    assert current["project_state"] == "A-T1 active"


def test_context_marks_old_cpu_evidence_stale(tmp_path):
    harness = load_harness()
    (tmp_path / "tasks").mkdir()
    (tmp_path / "tasks/backlog.json").write_text("[]", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/example.py").write_text("# before\n", encoding="utf-8")
    fingerprint = harness.source_snapshot(tmp_path)["fingerprint"]
    evidence = tmp_path / "runs/cpu-check-0001"
    evidence.mkdir(parents=True)
    (evidence / "gate.json").write_text(
        json.dumps({"status": "passed", "source_fingerprint": fingerprint}),
        encoding="utf-8",
    )
    assert harness.build_context(tmp_path)["latest_cpu"]["freshness"] == "current"
    (tmp_path / "scripts/example.py").write_text("# after\n", encoding="utf-8")
    assert harness.build_context(tmp_path)["latest_cpu"]["freshness"] == "stale"


def test_context_never_resurrects_superseded_plan(tmp_path, monkeypatch):
    harness = load_harness()
    (tmp_path / "tasks").mkdir()
    (tmp_path / "tasks/backlog.json").write_text("[]", encoding="utf-8")
    (tmp_path / "Research").mkdir()
    (tmp_path / "Research/DataMate_Research_Build_Plan.md").write_text(
        "superseded synthetic plan", encoding="utf-8"
    )

    def no_git_fallback(*args):
        raise AssertionError("must not consult Git for a superseded plan")

    monkeypatch.setattr(harness, "git_value", no_git_fallback)
    context = harness.build_context(tmp_path)
    assert context["timeline"]["status"] == "missing"
    assert "git_reference" not in context["timeline"]
    assert "plan" not in context
    assert any("Timeline" in warning for warning in context["warnings"])


def test_context_blocks_changed_docx_web_and_task_source(tmp_path):
    harness = load_harness()
    tasks = [{"id": "P0-SPLIT", "status": "todo", "depends_on": []}]
    synchronize_fixture(tmp_path, tasks)
    assert harness.build_context(tmp_path, "P0-SPLIT")["dependency_status"] == "ready"
    for path in (harness.TIMELINE, "Research/Timeline_DataMate_A-G.md"):
        original = (tmp_path / path).read_bytes()
        (tmp_path / path).write_bytes(original + b" changed")
        result = harness.build_context(tmp_path, "P0-SPLIT")
        assert result["dependency_status"] == "blocked"
        assert result["planning_errors"]
        (tmp_path / path).write_bytes(original)
    tasks[0]["source_sha256"] = "old-source"
    (tmp_path / "tasks/backlog.json").write_text(json.dumps(tasks), encoding="utf-8")
    assert harness.build_context(tmp_path, "P0-SPLIT")["dependency_status"] == "blocked"


def test_context_blocks_broken_graph_and_multiple_active_tasks(tmp_path):
    harness = load_harness()
    tasks = [
        {"id": "P0", "status": "todo", "depends_on": ["P1", "missing"]},
        {"id": "P1", "status": "todo", "depends_on": ["P0"]},
    ]
    synchronize_fixture(tmp_path, tasks)
    result = harness.build_context(tmp_path, "P0")
    assert result["dependency_status"] == "blocked"
    assert any("cycle" in error for error in result["planning_errors"])
    assert any("Unknown dependency" in error for error in result["planning_errors"])
    for t in tasks:
        t.update(status="in_progress", depends_on=[])
    synchronize_fixture(tmp_path, tasks)
    result = harness.build_context(tmp_path, "P0")
    assert any("Only one" in error for error in result["planning_errors"])


def test_context_serializes_work_and_requires_skip_decision(tmp_path):
    harness = load_harness()
    tasks = [
        {"id": "P8A", "status": "in_progress", "depends_on": [], "optional": True},
        {"id": "P9", "status": "todo", "depends_on": ["P8A"]},
    ]
    synchronize_fixture(tmp_path, tasks)
    result = harness.build_context(tmp_path, "P9")
    assert result["dependency_status"] == "blocked"
    assert result["other_active_tasks"] == ["P8A"]
    tasks[0]["status"] = "skipped"
    synchronize_fixture(tmp_path, tasks)
    assert harness.build_context(tmp_path, "P9")["dependency_status"] == "blocked"
    tasks[0]["skip_reason"] = "No improvement over the base model"
    synchronize_fixture(tmp_path, tasks)
    assert harness.build_context(tmp_path, "P9")["dependency_status"] == "ready"


def test_repository_phase_dependencies_and_source_are_current():
    harness = load_harness()
    result = harness.build_context(ROOT)
    assert result["planning_errors"] == []
    tasks = json.loads((ROOT / "tasks/backlog.json").read_text("utf-8"))
    by_id = {t["id"]: t for t in tasks}
    assert by_id["A-T1"]["status"] == by_id["A-T2"]["status"] == "done"
    assert "P0-SPLIT" in by_id["P0-TAXONOMY"]["depends_on"]
    assert by_id["P1"]["depends_on"] == ["P0-GATE"]
    for phase in range(3, 8):
        assert f"P{phase - 1}" in by_id[f"P{phase}"]["depends_on"]
    assert "P1" in by_id["P2"]["depends_on"]
    assert {"P7", "P8A", "P8B"} <= set(by_id["P9"]["depends_on"])
    assert "descriptor" in " ".join(by_id["P2"]["acceptance"]).lower()
