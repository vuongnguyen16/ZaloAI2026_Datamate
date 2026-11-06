"""CPU process boundaries. Trusted internal queries only; no SQL fallback API."""

import multiprocessing
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from datamate.scoring import parse_object
from datamate.serialization import MAX_RECORD_BYTES, exact_json


def _send(connection, result):
    raw = exact_json(result).encode("utf-8")
    if len(raw) > MAX_RECORD_BYTES:
        raw = b'{"status":"error","error":"output_budget"}'
    # Backend-defined Python objects must never be unpickled in the coordinator.
    connection.send_bytes(raw)


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
        _send(connection, {"status": "ok", "value": value})
    except Exception as exc:
        _send(connection, {"status": "error", "error": type(exc).__name__})
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
        _send(connection, {"status": "ok", "value": rows})
    except Exception as exc:
        _send(connection, {"status": "error", "error": type(exc).__name__})
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
    received = threading.Event()
    replies = []
    receiver = None

    def receive():
        try:
            raw = reader.recv_bytes(MAX_RECORD_BYTES)
            replies.append(parse_object(raw.decode("utf-8")))
        except (OSError, EOFError, ValueError, ArithmeticError, UnicodeError):
            replies.append({"status": "error", "error": "invalid_worker_result"})
        finally:
            received.set()

    try:
        process.start()
        writer.close()
        receiver = threading.Thread(target=receive, daemon=True)
        receiver.start()
        remaining = max(0.0, timeout_seconds - (time.monotonic() - started))
        if received.wait(remaining):
            result = replies[0]
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
        # Child end is closed after join, which releases a partial receive on EOF.
        if receiver is not None:
            receiver.join(0.5)
        reader.close()
        writer.close()
        process.close()


def run_bounded(function, args, timeout_seconds):
    return _supervise(_call_worker, (function, args), timeout_seconds)


def run_duckdb(
    database: Path, sql: str, parameters: list, timeout_seconds: float
) -> dict:
    return _supervise(_query_worker, (database, sql, parameters), timeout_seconds)
