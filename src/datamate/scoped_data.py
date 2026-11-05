"""Route JSONL by ID without decoding values outside the authorized partition."""

import hashlib
import json
import re
from pathlib import Path

from datamate.ingest.loader import is_link
from datamate.scoring import parse_object, validate_entry
from datamate.splits import append_event, authorize_access, open_split

MAX_LINE = 4 * 1024 * 1024
NUM = re.compile(rb"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")


def project_id(raw: bytes) -> str:
    """Inspect JSON syntax, top-level keys and id only; other strings stay bytes."""
    n = len(raw)

    def ws(i):
        while i < n and raw[i] in b" \t\r\n":
            i += 1
        return i

    def string_end(i):
        if i >= n or raw[i] != 34:
            raise ValueError("Expected JSON string envelope")
        i += 1
        while i < n:
            c = raw[i]
            if c == 34:
                return i + 1
            if c < 32:
                raise ValueError("Control byte in JSON string")
            if c == 92:
                i += 1
                if i >= n or raw[i] not in b'"\\/bfnrtu':
                    raise ValueError("Invalid JSON escape")
                if raw[i] == 117:
                    if i + 4 >= n or any(
                        c not in b"0123456789abcdefABCDEF" for c in raw[i + 1 : i + 5]
                    ):
                        raise ValueError("Invalid JSON unicode escape")
                    i += 4
            i += 1
        raise ValueError("Unterminated JSON string")

    def skip(i, depth=0):
        i = ws(i)
        if depth > 32 or i >= n:
            raise ValueError("JSON routing depth/length limit")
        c = raw[i]
        if c == 34:
            return string_end(i)
        if c in (91, 123):
            close = 93 if c == 91 else 125
            j = ws(i + 1)
            if j < n and raw[j] == close:
                return j + 1
            while True:
                if c == 123:
                    j = ws(string_end(j))
                    if j >= n or raw[j] != 58:
                        raise ValueError("Invalid object envelope")
                    j = ws(j + 1)
                j = ws(skip(j, depth + 1))
                if j < n and raw[j] == close:
                    return j + 1
                if j >= n or raw[j] != 44:
                    raise ValueError("Invalid nested JSON envelope")
                j = ws(j + 1)
        for literal in (b"true", b"false", b"null"):
            if raw.startswith(literal, i):
                return i + len(literal)
        match = NUM.match(raw, i)
        if match:
            return match.end()
        raise ValueError("Invalid JSON value envelope")

    i = ws(0)
    if i >= n or raw[i] != 123:
        raise ValueError("JSONL requires an object envelope")
    i = ws(i + 1)
    identifier = None
    keys = set()
    while i < n and raw[i] != 125:
        end = string_end(i)
        try:
            key = json.loads(raw[i:end])
        except (ValueError, UnicodeError) as exc:
            raise ValueError("Invalid top-level key encoding") from exc
        if key in keys:
            raise ValueError("Duplicate top-level JSON key")
        keys.add(key)
        i = ws(end)
        if i >= n or raw[i] != 58:
            raise ValueError("Missing key separator")
        i = ws(i + 1)
        end = skip(i)
        if key == "id":
            if raw[i] != 34:
                raise ValueError("ID must be a string token")
            try:
                identifier = json.loads(raw[i:end])
            except (ValueError, UnicodeError) as exc:
                raise ValueError("Invalid ID encoding") from exc
            if not isinstance(identifier, str) or not identifier.strip():
                raise ValueError("Nonempty string ID required")
        i = ws(end)
        if i < n and raw[i] == 44:
            i = ws(i + 1)
            if i < n and raw[i] == 125:
                raise ValueError("Trailing comma")
        elif i >= n or raw[i] != 125:
            raise ValueError("Invalid record separator")
    if i >= n or raw[i] != 125 or ws(i + 1) != n or identifier is None:
        raise ValueError("Invalid JSON record termination or missing ID")
    return identifier


def routed_records(
    path: Path,
    selected: set[str],
    universe: set[str],
    *,
    reference=False,
    progress=None,
) -> tuple[dict, dict]:
    if is_link(path) or not path.is_file() or path.stat().st_size > 128 * 1024 * 1024:
        raise ValueError("JSONL source missing, aliased or oversized")
    before = path.stat()
    seen, records = set(), {}
    h = hashlib.sha256()
    with path.open("rb") as handle:
        index = 0
        while raw := handle.readline(MAX_LINE + 1):
            index += 1
            h.update(raw)
            if len(raw) > MAX_LINE or index > 10000:
                raise ValueError("JSONL routing resource limit")
            line = raw.removeprefix(b"\xef\xbb\xbf") if index == 1 else raw
            try:
                qid = project_id(line)
            except ValueError as exc:
                raise ValueError(f"Invalid routing envelope at line {index}") from exc
            if qid in seen or qid not in universe:
                raise ValueError("Duplicate or unknown ID in scoped source")
            seen.add(qid)
            if qid in selected:
                if progress is not None:
                    progress["decode_attempts"] = progress.get("decode_attempts", 0) + 1
                try:
                    obj = parse_object(line)
                    if reference:
                        validate_entry(obj, reference=True)
                except (ValueError, TypeError) as exc:
                    raise ValueError(
                        f"Invalid authorized record at line {index}"
                    ) from exc
                records[qid] = obj
                if progress is not None:
                    progress["decoded_records"] = len(records)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("JSONL source changed during scoped read")
    if seen != universe or set(records) != selected:
        raise ValueError("Scoped source ID coverage differs from frozen manifest")
    return records, dict(
        file_sha256=h.hexdigest(),
        envelope_records=len(seen),
        decoded_records=len(records),
        skipped_value_records=len(seen) - len(records),
        value_decode_scope="authorized_ids_only",
    )


def read_scoped(
    split: Path,
    manifest_sha256: str,
    partition: str,
    resource: str,
    purpose: str,
    actor: str,
    candidate_sha256: str,
) -> tuple[dict, dict]:
    if resource not in {"questions", "gold"}:
        raise ValueError("Scoped reader only supports questions or gold")
    selected = set(
        authorize_access(
            split,
            manifest_sha256,
            partition,
            resource,
            purpose,
            actor,
            candidate_sha256,
        )
    )
    manifest, _ = open_split(split, manifest_sha256, verify_sources=True)
    source = Path(manifest["source"]["input_dir"])
    filename = "answers.jsonl" if resource == "gold" else "questions.jsonl"
    progress = {"decode_attempts": 0, "decoded_records": 0}
    try:
        records, audit = routed_records(
            source / filename,
            selected,
            set(manifest["source"]["questions"]),
            reference=resource == "gold",
            progress=progress,
        )
    except (ValueError, OSError) as exc:
        append_event(
            split,
            "access.jsonl",
            dict(
                kind="scoped_read_failed",
                partition=partition,
                resource=resource,
                purpose=purpose,
                actor=actor,
                candidate_sha256=candidate_sha256,
                manifest_sha256=manifest_sha256,
                gold_content_read=resource == "gold"
                and progress["decode_attempts"] > 0,
                error_class=type(exc).__name__,
                value_decode_scope="authorized_ids_only",
                **progress,
            ),
        )
        raise
    append_event(
        split,
        "access.jsonl",
        dict(
            kind="scoped_read_completed",
            partition=partition,
            resource=resource,
            purpose=purpose,
            actor=actor,
            candidate_sha256=candidate_sha256,
            manifest_sha256=manifest_sha256,
            gold_content_read=resource == "gold",
            **audit,
        ),
    )
    return records, audit
