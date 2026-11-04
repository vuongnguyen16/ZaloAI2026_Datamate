"""Exercise the developer gate in isolated, synthetic workspaces."""

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
    (tmp_path / "tasks/backlog.json").write_text(json.dumps(tasks), encoding="utf-8")
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
