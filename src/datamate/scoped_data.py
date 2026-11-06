"""Route JSONL by ID without decoding values outside the authorized partition."""

import hashlib
from pathlib import Path

from datamate.ingest.loader import is_link
from datamate.json_routing import project_id
from datamate.scoring import parse_object, validate_entry
from datamate.splits import append_event, authorize_access, open_split

MAX_LINE = 4 * 1024 * 1024


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
