"""Bounded subprocess supervision, usable without any GPU or cloud imports."""

import base64
import json
import os
import signal
import subprocess
import time
from pathlib import Path


def remaining_timeout(
    started: float, total: float, *, remaining_rounds: int, now: float | None = None
) -> float:
    available = total - ((time.monotonic() if now is None else now) - started) - 90
    if available <= 0 or remaining_rounds < 1:
        raise TimeoutError("probe deadline reserve reached")
    return available / remaining_rounds


def atomic_json(path: Path, value: dict) -> None:
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(encoded, encoding="utf-8")
    os.replace(temporary, path)


def read_checkpoint(path: Path) -> dict:
    if not path.is_file():
        return {"records": [], "checkpoint_error": "missing"}
    raw = path.read_bytes()
    try:
        result = json.loads(raw.decode("utf-8"))
        if not isinstance(result, dict):
            raise ValueError("checkpoint must be object")
        return result
    except (ValueError, UnicodeError):
        return {
            "records": [],
            "checkpoint_error": "unreadable",
            "checkpoint_raw_base64": base64.b64encode(raw).decode("ascii"),
        }


def checkpoint_round(directory: Path, result: dict, commit) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    atomic_json(directory / "round.json", result)
    commit()


def run_child(
    command: list[str], directory: Path, *, timeout: float, sample_memory
) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    peak, samples, timed_out = 0, 0, False
    started = time.time()
    monotonic_started = time.monotonic()
    kwargs = {"start_new_session": True} if os.name != "nt" else {}
    with (
        (directory / "stdout.log").open("wb") as out,
        (directory / "stderr.log").open("wb") as err,
    ):
        child = subprocess.Popen(command, stdout=out, stderr=err, **kwargs)
        try:
            while True:
                measured = sample_memory()
                if type(measured) is int and measured >= 0:
                    peak = max(peak, measured)
                    samples += 1
                if child.poll() is not None:
                    break
                if time.monotonic() - monotonic_started >= timeout:
                    timed_out = True
                    break
                time.sleep(0.05)
        finally:
            if os.name != "nt":
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif child.poll() is None:
                child.kill()
            child.wait(timeout=10)
    cleaned = child.poll() is not None
    if os.name != "nt":
        # A surviving process group, including orphan workers, invalidates cleanup.
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            pass
        else:
            cleaned = False
    return {
        "pid": child.pid,
        "engine_started_at": started,
        "duration_seconds": time.time() - started,
        "exit_code": child.returncode,
        "timed_out": timed_out,
        "cleaned_up": cleaned,
        "peak_memory_bytes": peak,
        "memory_sample_count": samples,
    }
