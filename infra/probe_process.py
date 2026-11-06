"""Bounded subprocess supervision, usable without any GPU or cloud imports."""

import os
import signal
import subprocess
import time
from pathlib import Path


def run_child(
    command: list[str], directory: Path, *, timeout: float, sample_memory
) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    peak, samples, timed_out = 0, 0, False
    started = time.time()
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
                if time.time() - started >= timeout:
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
