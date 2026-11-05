"""Source boundaries and freshness for the optional graph navigation tool."""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/graphify_local.py"
spec = importlib.util.spec_from_file_location("graphify_local", SCRIPT)
graphify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graphify)


def workspace(root):
    (root / "src").mkdir()
    (root / "src/module.py").write_text("def hello(): pass\n", encoding="utf-8")
    (root / "graphify-out").mkdir()
    (root / "graphify-out/graph.json").write_text(
        json.dumps(
            {"nodes": [{"id": "hello", "source_file": "src/module.py"}], "links": []}
        ),
        encoding="utf-8",
    )
    return graphify.snapshot(root)


def save_receipt(root, sources):
    result = {**sources, **graphify.graph_summary(root, sources)}
    (root / "graphify-out/datamate_receipt.json").write_text(
        json.dumps(result), encoding="utf-8"
    )


def test_only_code_and_fixed_settings_are_fingerprinted(tmp_path):
    first = workspace(tmp_path)
    for name in ("data/gold.jsonl", "runs/results.json", "new_private_tree/gold.py"):
        path = tmp_path / name
        path.parent.mkdir(exist_ok=True)
        path.write_text("synthetic private fixture", encoding="utf-8")
    assert graphify.snapshot(tmp_path) == first
    settings = tmp_path / "tools/graphify"
    settings.mkdir(parents=True)
    (settings / "uv.lock").write_text("version=1\n", encoding="utf-8")
    assert graphify.snapshot(tmp_path) != first


def test_freshness_detects_source_edits_and_deleted_files(tmp_path):
    sources = workspace(tmp_path)
    save_receipt(tmp_path, sources)
    assert graphify.current_status(tmp_path, sources)["status"] == "current"
    (tmp_path / "src/module.py").write_text("def changed(): pass\n", encoding="utf-8")
    assert (
        graphify.current_status(tmp_path, graphify.snapshot(tmp_path))["status"]
        == "stale"
    )
    (tmp_path / "src/module.py").unlink()
    assert (
        graphify.current_status(tmp_path, graphify.snapshot(tmp_path))["status"]
        == "stale"
    )


@pytest.mark.parametrize(
    "source", ["data/gold.py", "src/../data/gold.py", "src/gold.jsonl"]
)
def test_graph_rejects_sources_outside_scope(tmp_path, source):
    sources = workspace(tmp_path)
    (tmp_path / "graphify-out/graph.json").write_text(
        json.dumps({"nodes": [{"id": "private", "source_file": source}]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="outside the code scope"):
        graphify.graph_summary(tmp_path, sources)


def test_query_process_disables_backends_and_global_logging(tmp_path, monkeypatch):
    monkeypatch.setattr(graphify, "ROOT", tmp_path)
    executable = (
        tmp_path
        / "tools/graphify/.venv"
        / ("Scripts/python.exe" if graphify.os.name == "nt" else "bin/python")
    )
    executable.parent.mkdir(parents=True)
    executable.touch()
    monkeypatch.setenv("GRAPHIFY_BACKEND", "gemini")
    monkeypatch.setenv("GRAPHIFY_OUT", "data")
    calls = []
    monkeypatch.setattr(
        graphify.subprocess, "run", lambda *a, **kw: calls.append((a, kw))
    )
    graphify.run_graphify(["query", "hello", "--budget", "1200"])
    args, kwargs = calls[0]
    assert args[0][1:] == ["-m", "graphify", "query", "hello", "--budget", "1200"]
    assert kwargs["env"]["GRAPHIFY_BACKEND"] == "none"
    assert kwargs["env"]["GRAPHIFY_QUERY_LOG_DISABLE"] == "1"
    assert kwargs["env"]["GRAPHIFY_OUT"] == "graphify-out"
    assert kwargs["cwd"] == tmp_path
    assert kwargs["check"] is True
