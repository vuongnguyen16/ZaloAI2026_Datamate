"""Single-writer, append-only prediction checkpoints and no-clobber publication."""

import errno
import hashlib
import os
import shutil
import uuid
from pathlib import Path

from datamate.ingest.loader import is_link
from datamate.scoring import parse_object
from datamate.serialization import MAX_RECORD_BYTES, exact_json, submission_bytes

MAX_STORE_BYTES = 512 * 1024 * 1024
MAX_JOURNAL_RECORDS = 100000


def journal_lines(paths):
    total, count = 0, 0
    for path in paths:
        safe_path(path)
        if not path.is_file() or path.stat().st_nlink != 1:
            raise ValueError("not a regular unlinked file")
        with path.open("rb") as handle:
            index = 0
            while line := handle.readline(MAX_RECORD_BYTES + 1):
                index += 1
                count += 1
                total += len(line)
                if count > MAX_JOURNAL_RECORDS or len(line) > MAX_RECORD_BYTES:
                    raise ValueError("checkpoint record budget exceeded")
                if total > MAX_STORE_BYTES:
                    raise ValueError("checkpoint store exceeds byte budget")
                yield path, index, line


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


def publish(path: Path, data: bytes, *, allow_exclusive_fallback=False) -> dict:
    return publish_chunks(
        path, (data,), allow_exclusive_fallback=allow_exclusive_fallback
    )


def publish_chunks(
    path: Path, chunks, max_bytes=None, *, allow_exclusive_fallback=False
) -> dict:
    """Link a fsynced sibling inode exclusively. A conflict retains our pending file."""
    path = safe_path(path)
    limit = MAX_STORE_BYTES if max_bytes is None else min(max_bytes, MAX_STORE_BYTES)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{uuid.uuid4().hex}.pending")
    digest, size = hashlib.sha256(), 0
    with pending.open("xb") as handle:
        for chunk in chunks:
            size += len(chunk)
            if size > limit:
                raise ValueError(
                    "publication exceeds byte budget; pending candidate preserved"
                )
            digest.update(chunk)
            handle.write(chunk)
        handle.flush()
        os.fsync(handle.fileno())
    mode = "atomic_hardlink"
    try:
        try:
            os.link(pending, path)
        except FileExistsError:
            raise
        except OSError as exc:
            if not allow_exclusive_fallback or exc.errno not in {
                errno.EXDEV,
                errno.ENOSYS,
                errno.ENOTSUP,
                errno.EOPNOTSUPP,
            }:
                raise
            mode = "non_atomic_exclusive"
            # O_EXCL refuses an existing/racing path, including a symlink.
            # Never delete a partial final if this copy is interrupted.
            with path.open("xb") as dest, pending.open("rb") as source:
                shutil.copyfileobj(source, dest, 1024 * 1024)
                dest.flush()
                os.fsync(dest.fileno())
        status = "published"
    except FileExistsError:
        safe_path(path)
        existing = hashlib.sha256()
        if not path.is_file() or path.stat().st_size != size:
            raise FileExistsError(f"output conflict; candidate preserved at {pending}")
        with path.open("rb") as handle:
            read = 0
            while block := handle.read(1024 * 1024):
                read += len(block)
                if read > limit:
                    raise FileExistsError(
                        "output conflict; file grew during comparison"
                    )
                existing.update(block)
        if read != size or existing.digest() != digest.digest():
            raise FileExistsError(f"output conflict; candidate preserved at {pending}")
        status = "reused"
        mode = "existing_verified"
    pending.unlink()
    try:
        directory_sync = sync_directory(path.parent)
    except OSError as exc:
        if not allow_exclusive_fallback or exc.errno not in {
            errno.EINVAL,
            errno.ENOSYS,
            errno.ENOTSUP,
            errno.EOPNOTSUPP,
        }:
            raise
        directory_sync = f"unavailable_filesystem_errno_{exc.errno}"
    return {
        "status": status,
        "mode": mode,
        "sha256": digest.hexdigest(),
        "directory_sync": directory_sync,
    }


class RunStore:
    def __init__(self, output: Path, identity: dict, *, allow_exclusive_fallback=False):
        self.output = safe_path(output)
        self.identity = identity
        self.errors = []
        self.lock = None
        self.segment = None
        self.bytes_written = 0
        self.allow_exclusive_fallback = allow_exclusive_fallback

    def __enter__(self):
        self.output.mkdir(parents=True, exist_ok=True)
        manifest = self.output / "identity.json"
        expected = (exact_json(self.identity) + "\n").encode("utf-8")
        marker = self.output / f".init-{hashlib.sha256(expected).hexdigest()}.marker"
        # A nonempty /result is allowed only when it belongs to this exact run.
        if not manifest.exists():
            children = list(self.output.iterdir())
            if children and (
                not marker.is_file()
                or regular_bytes(marker, 1, single_link=True) != b""
                or any(
                    p != marker
                    and not (
                        p.name.startswith(".identity.json.")
                        and p.name.endswith(".pending")
                        and p.is_file()
                        and not is_link(p)
                        and p.stat().st_nlink == 1
                    )
                    for p in children
                )
            ):
                raise ValueError("foreign nonempty output directory")
            try:
                with marker.open("xb") as handle:
                    handle.flush()
                    os.fsync(handle.fileno())
            except FileExistsError:
                if regular_bytes(marker, 1, single_link=True) != b"":
                    raise ValueError("foreign initialization marker")
            sync_directory(self.output)
            if self.allow_exclusive_fallback:
                publish(manifest, expected, allow_exclusive_fallback=True)
            else:
                publish(manifest, expected)
        if regular_bytes(manifest, MAX_RECORD_BYTES) != expected:
            raise ValueError("checkpoint identity mismatch")
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
            self.bytes_written = sum(
                p.stat().st_size for p in self.output.glob("segment-*.jsonl")
            )
            if self.bytes_written > MAX_STORE_BYTES:
                raise ValueError("checkpoint store exceeds byte budget")
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
        if self.bytes_written + len(raw) > MAX_STORE_BYTES:
            raise ValueError("checkpoint store exceeds byte budget")
        self.segment.write(raw)
        self.segment.flush()
        os.fsync(self.segment.fileno())
        self.bytes_written += len(raw)

    def recover(self) -> dict:
        results = {}
        self.errors = []
        paths = sorted(self.output.glob("segment-*.jsonl"))
        if len(paths) > 10000:
            raise ValueError("checkpoint segment budget exceeded")
        for path, index, line in journal_lines(paths):
            if not line.endswith(b"\n"):
                self.errors.append({"kind": "torn_tail", "segment": path.name})
                continue
            try:
                obj = parse_object(line)
                canonical = submission_bytes(obj)
            except (
                ValueError,
                TypeError,
                UnicodeError,
                ArithmeticError,
                RecursionError,
            ):
                self.errors.append(
                    {"kind": "invalid_checkpoint", "segment": path.name, "line": index}
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
