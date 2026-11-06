"""Single-writer, append-only prediction checkpoints and no-clobber publication."""

import hashlib
import os
import uuid
from pathlib import Path

from datamate.ingest.loader import is_link
from datamate.scoring import parse_object
from datamate.serialization import MAX_RECORD_BYTES, exact_json, submission_bytes

MAX_STORE_BYTES = 512 * 1024 * 1024


def safe_path(path: Path) -> Path:
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        if is_link(part):
            raise ValueError("linked/reparse path refused")
    return path


def sync_directory(path: Path) -> str:
    if os.name == "nt":
        return "unavailable_windows_process_crash_only"
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return "fsynced"


def regular_bytes(path: Path, limit=MAX_STORE_BYTES, *, single_link=False) -> bytes:
    safe_path(path)
    if not path.is_file() or (single_link and path.stat().st_nlink != 1):
        raise ValueError("not a regular unlinked file")
    with path.open("rb") as handle:
        result = handle.read(limit + 1)
    if len(result) > limit:
        raise ValueError("file exceeds byte budget")
    return result


def publish(path: Path, data: bytes) -> dict:
    """Link a fsynced sibling inode exclusively. A conflict retains our pending file."""
    path = safe_path(path)
    if len(data) > MAX_STORE_BYTES:
        raise ValueError("publication exceeds byte budget")
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{uuid.uuid4().hex}.pending")
    with pending.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.link(pending, path)
        status = "published"
    except FileExistsError:
        if regular_bytes(path) != data:
            raise FileExistsError(f"output conflict; candidate preserved at {pending}")
        status = "reused"
    pending.unlink()
    return {
        "status": status,
        "sha256": hashlib.sha256(data).hexdigest(),
        "directory_sync": sync_directory(path.parent),
    }


class RunStore:
    def __init__(self, output: Path, identity: dict):
        self.output = safe_path(output)
        self.identity = identity
        self.errors = []
        self.lock = None
        self.segment = None

    def __enter__(self):
        self.output.mkdir(parents=True, exist_ok=True)
        manifest = self.output / "identity.json"
        # A nonempty /result is allowed only when it belongs to this exact run.
        if not manifest.exists() and any(self.output.iterdir()):
            raise ValueError("foreign nonempty output directory")
        lock_path = safe_path(self.output / ".writer.lock")
        if lock_path.exists() and lock_path.stat().st_nlink != 1:
            raise ValueError("linked writer lock")
        self.lock = lock_path.open("a+b")
        try:
            self.lock.seek(0, os.SEEK_END)
            if not self.lock.tell():
                self.lock.write(b"0")
                self.lock.flush()
            self.lock.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            expected = (exact_json(self.identity) + "\n").encode("utf-8")
            if manifest.exists():
                if regular_bytes(manifest, MAX_RECORD_BYTES) != expected:
                    raise ValueError("checkpoint identity mismatch")
            else:
                publish(manifest, expected)
            # Historical segments are never reopened for append.
            segment_path = self.output / f"segment-{uuid.uuid4().hex}.jsonl"
            self.segment = segment_path.open("xb")
            sync_directory(self.output)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        if self.segment is not None:
            self.segment.close()
            self.segment = None
        if self.lock is not None:
            # Closing releases the OS lock even after an interrupted process.
            self.lock.close()
            self.lock = None

    def append(self, record: dict):
        raw = submission_bytes(record)
        self.segment.write(raw)
        self.segment.flush()
        os.fsync(self.segment.fileno())

    def recover(self) -> dict:
        results, total = {}, 0
        self.errors = []
        for path in sorted(self.output.glob("segment-*.jsonl")):
            raw = regular_bytes(path, single_link=True)
            total += len(raw)
            if total > MAX_STORE_BYTES:
                raise ValueError("checkpoint store exceeds byte budget")
            lines = raw.splitlines(keepends=True)
            for index, line in enumerate(lines):
                if not line.endswith(b"\n"):
                    self.errors.append({"kind": "torn_tail", "segment": path.name})
                    continue
                try:
                    if len(line) > MAX_RECORD_BYTES:
                        raise ValueError("checkpoint record too large")
                    obj = parse_object(line)
                    canonical = submission_bytes(obj)
                except (ValueError, TypeError, UnicodeError):
                    self.errors.append(
                        {
                            "kind": "invalid_checkpoint",
                            "segment": path.name,
                            "line": index + 1,
                        }
                    )
                    continue
                qid = obj["id"]
                if qid in results and submission_bytes(results[qid]) != canonical:
                    results[qid] = {
                        "id": qid,
                        "type": "abstain",
                        "reason": "checkpoint_conflict",
                    }
                    self.errors.append({"kind": "checkpoint_conflict", "id": qid})
                else:
                    results[qid] = obj
        return results
