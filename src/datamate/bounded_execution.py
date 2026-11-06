"""CPU process boundaries. Trusted internal queries only; no SQL fallback API."""

import multiprocessing
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from datamate.serialization import MAX_RECORD_BYTES, exact_json


@dataclass(frozen=True)
class Deadline:
    started: float
    budget: float
    reserve: float

    def __post_init__(self):
        if not 0 <= self.reserve < self.budget or self.budget > 21600:
            raise ValueError("invalid deadline budget/reserve")

    @property
    def remaining(self):
        return max(0.0, self.started + self.budget - time.monotonic())

    @property
    def work_remaining(self):
        return max(0.0, self.remaining - self.reserve)


def _call_worker(connection, stop, function, args):
    try:
        value = function(*args)
        if len(exact_json(value).encode("utf-8")) > MAX_RECORD_BYTES:
            raise ValueError("worker output exceeds byte budget")
        connection.send({"status": "ok", "value": value})
    except Exception as exc:
        connection.send({"status": "error", "error": type(exc).__name__})
    finally:
        connection.close()


def _query_worker(connection, stop, database, sql, parameters):
    import duckdb

    con = None
    done = threading.Event()
    try:
        con = duckdb.connect(
            str(database),
            read_only=True,
            config={
                "enable_external_access": "false",
                "threads": "2",
                "memory_limit": "256MB",
            },
        )

        def interrupt():
            while not done.wait(0.01):
                if stop.is_set():
                    con.interrupt()

        controller = threading.Thread(target=interrupt, daemon=True)
        controller.start()
        rows = con.execute(sql, parameters).fetchmany(10001)
        if len(rows) > 10000:
            raise ValueError("query row budget exceeded")
        rows = [list(row) for row in rows]
        if len(exact_json(rows).encode("utf-8")) > MAX_RECORD_BYTES:
            raise ValueError("query byte budget exceeded")
        connection.send({"status": "ok", "value": rows})
    except Exception as exc:
        connection.send({"status": "error", "error": type(exc).__name__})
    finally:
        done.set()
        if con is not None:
            if "controller" in locals():
                controller.join()
            con.close()
        connection.close()


def _supervise(target, args, timeout_seconds):
    if timeout_seconds <= 0:
        return {"status": "timeout", "cleanup": "not_started"}
    started = time.monotonic()
    context = multiprocessing.get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    stop = context.Event()
    process = context.Process(target=target, args=(writer, stop, *args))
    try:
        process.start()
        writer.close()
        remaining = max(0.0, timeout_seconds - (time.monotonic() - started))
        if reader.poll(remaining):
            try:
                result = reader.recv()
            except EOFError:
                result = {"status": "error", "error": "worker_exited"}
        else:
            result = {"status": "timeout"}
        stop.set()
        process.join(0.25)
        if process.is_alive():
            process.terminate()
            process.join(0.5)
            result["cleanup"] = "terminated"
        else:
            result["cleanup"] = "joined"
        if process.is_alive():
            process.kill()
            process.join()
            result["cleanup"] = "killed"
        return result
    finally:
        stop.set()
        if process.pid is not None and process.is_alive():
            process.kill()
            process.join()
        reader.close()
        writer.close()
        process.close()


def run_bounded(function, args, timeout_seconds):
    return _supervise(_call_worker, (function, args), timeout_seconds)


def run_duckdb(
    database: Path, sql: str, parameters: list, timeout_seconds: float
) -> dict:
    return _supervise(_query_worker, (database, sql, parameters), timeout_seconds)
