"""Read-only local inventory. Does not inspect tokens or launch cloud jobs."""

import ctypes
import json
import os
import platform
import shutil
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import yaml


def windows_memory() -> dict:
    if os.name != "nt":
        return {"status": "not_measured_on_this_platform"}

    class Memory(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong)
            for name in (
                "total_phys",
                "avail_phys",
                "total_page",
                "avail_page",
                "total_virtual",
                "avail_virtual",
                "avail_extended",
            )
        ]

    memory = Memory()
    memory.length = ctypes.sizeof(memory)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
        return {"status": "unavailable"}
    return {"total_bytes": memory.total_phys, "available_bytes": memory.avail_phys}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    packages = {}
    for name in ("datamate", "duckdb", "pydantic", "pyyaml", "pytest", "ruff", "modal"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = "not_installed"
    report = {
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "cpu_identifier": os.environ.get("PROCESSOR_IDENTIFIER", platform.processor()),
        "logical_cpus": os.cpu_count(),
        "memory": windows_memory(),
        "workspace_disk_bytes": dict(
            zip(("total", "used", "free"), shutil.disk_usage(root))
        ),
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "in_venv": sys.prefix != sys.base_prefix,
        "packages": packages,
        "git": shutil.which("git"),
        "docker": shutil.which("docker"),
        "local_policy": {
            "threads": 2,
            "duckdb_memory_mb": 256,
            "fixture_max_bytes": 1048576,
        },
        "modal": {
            "profile": "vuonghungnguyen07",
            "workspace": "vuonghungnguyen07",
            "authentication": "not_checked_by_doctor; see reports/s00_setup.md",
            "budget_usd_per_experiment": yaml.safe_load(
                (root / "configs/modal_dev.yaml").read_text("utf-8")
            )["budget_usd_per_experiment"],
            "job_started": False,
        },
        "gpu": "not_tested",
        "pa": "not_evaluated",
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    required = ("datamate", "duckdb", "pydantic", "pyyaml", "pytest", "ruff")
    return (
        0
        if report["in_venv"] and all(packages[p] != "not_installed" for p in required)
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
