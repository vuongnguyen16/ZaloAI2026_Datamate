"""Bounded local Graphify CLI for DataMate; never selects an LLM backend."""

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TREES = ("src", "scripts", "tests", "infra")
SETTINGS = (
    ".graphifyignore",
    ".graphifyrc",
    ".gitignore",
    "tools/graphify/pyproject.toml",
    "tools/graphify/uv.lock",
)
OUT = "graphify-out"


def reject_link(path: Path) -> None:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024:
        raise ValueError(f"linked/reparse path is outside this tool's scope: {path}")


def snapshot(root: Path) -> dict:
    """Read Python source and fixed config only, without traversing other trees."""
    paths = []
    for tree in TREES:
        base = root / tree
        if not base.exists():
            continue
        reject_link(base)
        for directory, dirs, files in os.walk(base, followlinks=False):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in dirs + files:
                reject_link(Path(directory) / name)
            paths.extend(Path(directory) / f for f in files if f.endswith(".py"))
    for name in SETTINGS:
        path = root / name
        if path.exists():
            # Check parents before opening a fixed config through a junction.
            for parent in path.relative_to(root).parents:
                reject_link(root / parent)
            reject_link(path)
            paths.append(path)
    hashes = {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths)
    }
    return {
        "files": hashes,
        "fingerprint": hashlib.sha256(
            json.dumps(hashes, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }


def graph_summary(root: Path, sources: dict) -> dict:
    graph = json.loads((root / OUT / "graph.json").read_text("utf-8"))
    for item in graph.get("nodes", []) + graph.get("links", graph.get("edges", [])):
        source = item.get("source_file")
        if source:
            path = Path(source.replace("\\", "/"))
            if (
                path.is_absolute()
                or ".." in path.parts
                or not path.parts
                or path.parts[0] not in TREES
                or path.suffix != ".py"
            ):
                raise ValueError(
                    f"graph contains a source outside the code scope: {source}"
                )
        if item.get("_origin") == "semantic":
            raise ValueError(
                "graph contains semantic extraction; use a fresh code graph"
            )
    if not graph.get("nodes"):
        raise ValueError("graph has no nodes")
    return {
        "nodes": len(graph["nodes"]),
        "edges": len(graph.get("links", graph.get("edges", []))),
        "source_files": len(
            {n["source_file"] for n in graph["nodes"] if n.get("source_file")}
        ),
        "graph_sha256": hashlib.sha256(
            (root / OUT / "graph.json").read_bytes()
        ).hexdigest(),
    }


def current_status(root: Path, sources: dict) -> dict:
    receipt = root / OUT / "datamate_receipt.json"
    if not receipt.is_file() or not (root / OUT / "graph.json").is_file():
        return {"status": "missing", "next": "python scripts/graphify_local.py build"}
    saved = json.loads(receipt.read_text("utf-8"))
    summary = graph_summary(root, sources)
    current = (
        saved.get("fingerprint") == sources["fingerprint"]
        and saved.get("graph_sha256") == summary["graph_sha256"]
    )
    return {"status": "current" if current else "stale", **summary}


def run_graphify(arguments: list[str]) -> None:
    executable = (
        ROOT
        / "tools/graphify/.venv"
        / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    if not executable.is_file():
        raise ValueError("run uv sync --project tools/graphify --locked first")
    env = {
        **os.environ,
        "GRAPHIFY_OUT": OUT,
        "GRAPHIFY_BACKEND": "none",
        "GRAPHIFY_QUERY_LOG_DISABLE": "1",
        "OMP_NUM_THREADS": "2",
        "OPENBLAS_NUM_THREADS": "2",
        "PYTHONIOENCODING": "utf-8",
    }
    subprocess.run(
        [str(executable), "-m", "graphify", *arguments],
        cwd=ROOT,
        env=env,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "update", "status", "html"):
        commands.add_parser(name)
    query = commands.add_parser("query")
    query.add_argument("question")
    query.add_argument("--budget", type=int, metavar="100..4000", default=1200)
    query.add_argument("--depth", type=int, choices=range(1, 4), default=1)
    commands.add_parser("explain").add_argument("node")
    path = commands.add_parser("path")
    path.add_argument("source")
    path.add_argument("target")
    args = parser.parse_args()
    if args.command == "query" and not 100 <= args.budget <= 4000:
        parser.error("--budget must be between 100 and 4000")
    try:
        sources = snapshot(ROOT)
        output = ROOT / OUT
        if output.exists():
            reject_link(output)
        if args.command in ("build", "update"):
            if (output / "memory").exists():
                raise ValueError(
                    "Graphify memory sidecar is outside the code-only scope"
                )
            if (output / "graph.json").exists():
                graph_summary(ROOT, sources)
            # Explicit CLI exclusions keep new root-level paths out even if an
            # ignore rule is accidentally weakened. Nested ignore rules still apply.
            excludes = [
                part
                for p in sorted(ROOT.iterdir())
                if p.name not in TREES
                for part in ("--exclude", "/" + p.name)
            ]
            run_graphify(
                ["extract", ".", "--code-only", "--max-workers", "2", *excludes]
            )
            if snapshot(ROOT) != sources:
                raise ValueError("code/config changed during build; run update again")
            result = {**sources, **graph_summary(ROOT, sources), "backend": "none"}
            (output / "datamate_receipt.json").write_text(
                json.dumps(result, indent=2) + "\n", encoding="utf-8"
            )
            print(json.dumps(current_status(ROOT, sources)))
            return 0
        status = current_status(ROOT, sources)
        if args.command == "status":
            print(json.dumps(status))
            return 0 if status["status"] == "current" else 2
        if status["status"] != "current":
            raise ValueError(
                "graph missing/stale; run python scripts/graphify_local.py update"
            )
        if args.command == "query":
            run_graphify(
                [
                    "query",
                    args.question,
                    "--budget",
                    str(args.budget),
                    "--depth",
                    str(args.depth),
                ]
            )
        elif args.command == "explain":
            run_graphify(["explain", args.node])
        elif args.command == "path":
            run_graphify(["path", args.source, args.target])
        elif args.command == "html":
            run_graphify(["export", "html"])
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"Graphify: {exc}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        return exc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
