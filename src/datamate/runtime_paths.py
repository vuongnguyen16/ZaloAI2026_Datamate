"""Submission filesystem guards and ownership, without pipeline dependencies."""

import os
import threading
from contextlib import contextmanager
from pathlib import Path

_owned = threading.local()


class OutputBusyError(OSError):
    """Another live writer owns this output; fallback must not compete."""


def is_link(path):
    return path.is_symlink() or (
        path.exists() and bool(getattr(path.lstat(), "st_file_attributes", 0) & 0x400)
    )


def disjoint(a, b):
    return a != b and a not in b.parents and b not in a.parents


def safe_path(path):
    path = Path(os.path.abspath(path))
    if any(is_link(part) for part in (path, *path.parents)):
        raise ValueError("linked/reparse path refused")
    return path


def output_layout(output):
    output = safe_path(output)
    if output.exists():
        for path in output.iterdir():
            if path.name not in {"logs", "submission.jsonl"}:
                continue
            safe_path(path)
            if path.name == "logs" and path.is_dir():
                continue
            if path.name == "submission.jsonl" and path.is_file():
                continue
            raise ValueError("owned output path type conflict")
    return output / "logs" / ".state"


def ignored_output_entries(output):
    output = safe_path(output)
    if not output.exists():
        return []
    # Names only. Unknown entries may be unreadable files or external links.
    return sorted(
        path.name
        for path in output.iterdir()
        if path.name not in {"logs", "submission.jsonl"}
    )


@contextmanager
def publication_lock(output):
    state = output_layout(output)
    path = safe_path(state.parent / ".publication.lock")
    key = os.path.normcase(str(path))
    owned = getattr(_owned, "paths", None)
    if owned is None:
        owned = _owned.paths = set()
    if key in owned:
        yield
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and (
        not path.is_file() or path.stat().st_nlink != 1 or path.stat().st_size > 1
    ):
        raise ValueError("invalid publication lock")
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if not handle.tell():
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise OutputBusyError("output publication lock unavailable") from exc
        owned.add(key)
        try:
            yield
        finally:
            owned.remove(key)
