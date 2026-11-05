"""Gold-free split freezing and application-level access/audit contracts."""

import hashlib
import json
import os
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

from datamate.artifacts import sha256
from datamate.contracts import json_object
from datamate.ingest.loader import (
    business_path,
    disjoint,
    identifier,
    is_link,
    snapshot,
)
from datamate.ingest.model import LoaderOptions
from datamate.ingest.text_format import inspect_encoding
from datamate.runner import read_questions

PARTITIONS = ("dev", "calibration", "holdout")
HEX = re.compile(r"[0-9a-f]{64}")


def encoded(obj) -> bytes:
    return (
        json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def digest(obj) -> str:
    return hashlib.sha256(encoded(obj)).hexdigest()


def load_json(path: Path) -> dict:
    if is_link(path) or not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("JSON artifact missing, aliased or oversized")
    return json_object(path.read_text("utf-8"))


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def header_template(columns: list[str]) -> str:
    # Match the full-header grid encoding used by A-T2 freeze_labels.py.
    grid = [
        [
            (str(i), unicodedata.normalize("NFC", name).casefold().strip())
            for i, name in enumerate(columns, 1)
            if name
        ]
    ]
    return hashlib.sha256(json.dumps(grid, ensure_ascii=False).encode()).hexdigest()


def unit_names(path: Path) -> set[str]:
    if path.suffix.lower() == ".csv":
        return {path.stem}
    with ZipFile(path) as archive:
        info = archive.getinfo("xl/workbook.xml")
        if info.file_size > 8 * 1024 * 1024:
            raise ValueError("Workbook metadata exceeds limit")
        raw = archive.read(info)
        if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise ValueError("Unsafe workbook metadata")
        doc = ET.fromstring(raw)
        return {n.attrib["name"] for n in doc.iter() if n.tag.endswith("}sheet")}


def catalog(input_dir: Path, labels_path: Path, labels_sha256: str) -> dict:
    try:
        return _catalog(input_dir, labels_path, labels_sha256)
    except (KeyError, TypeError, sqlite3.Error, ET.ParseError, BadZipFile) as exc:
        raise ValueError("Invalid structural labels or source catalog") from exc


def _catalog(input_dir: Path, labels_path: Path, labels_sha256: str) -> dict:
    source = input_dir.resolve(strict=True)
    if source.name != "train" or not source.is_dir() or is_link(input_dir):
        raise ValueError("Split freeze accepts a non-aliased train directory only")
    if not disjoint(source, labels_path.resolve()) or is_link(labels_path):
        raise ValueError("Structural evidence must be outside source, without aliases")
    data = source / "data"
    if not data.is_dir() or is_link(data):
        raise ValueError("Missing or aliased data directory")
    paths = sorted(data.iterdir())
    if not 3 <= len(paths) <= 200:
        raise ValueError("Split requires 3..200 businesses")
    files, signatures, businesses, layouts, formats = {}, defaultdict(set), {}, {}, {}
    for path in paths:
        business = business_path(source, path.name)
        records = snapshot(business, LoaderOptions())
        businesses[path.name] = records
        for record in records:
            relative = f"data/{path.name}/{record['path']}"
            files[relative] = record["sha256"]
            if record["path"] != "README.md":
                signatures[("file", record["sha256"])].add(path.name)
        readme = business / "README.md"
        lines = readme.read_text(inspect_encoding(readme)["encoding"]).splitlines()
        preamble = next(
            (
                normalize(line)
                for line in lines
                if line.strip() and not line.startswith("#")
            ),
            "",
        )
        if not preamble:
            raise ValueError("README requires a layout preamble")
        layouts[path.name] = hashlib.sha256(preamble.encode()).hexdigest()
        signatures[("readme_layout", layouts[path.name])].add(path.name)
        formats[path.name] = sorted(
            {
                Path(r["path"]).suffix.lower()
                for r in records
                if r["path"] != "README.md"
            }
        )

    for name in ("questions.jsonl", "rulebook.md", "calendar.csv"):
        p = source / name
        if is_link(p) or not p.is_file() or not p.resolve().is_relative_to(source):
            raise ValueError("Required input file missing or aliased")
        files[name] = sha256(p)
    if (source / "questions.jsonl").stat().st_size > 32 * 1024 * 1024:
        raise ValueError("Question metadata exceeds limit")
    questions = read_questions(source / "questions.jsonl", limit=10000)
    membership = {q.id: q.business_id for q in questions}
    if set(membership.values()) != set(businesses):
        raise ValueError("Question business coverage differs from source businesses")

    if not HEX.fullmatch(labels_sha256) or sha256(labels_path) != labels_sha256:
        raise ValueError("Structural labels hash differs from expected frozen evidence")
    labels = load_json(labels_path)
    covered = defaultdict(set)
    for record in labels["records"]:
        bid, name = record["business_id"], record["source_file"]
        key = f"data/{bid}/{name}"
        if (
            key not in files
            or files[key] != record["source_sha256"]
            or files.get(f"data/{bid}/README.md") != record["readme_sha256"]
        ):
            raise ValueError("Structural labels are stale or reference unknown sources")
        if Path(name).suffix.lower() not in {".csv", ".xlsx"}:
            raise ValueError("A-T2 labels must refer to CSV/XLSX units")
        unit = record["source_name"]
        if unit in covered[key] or not HEX.fullmatch(record["template"]):
            raise ValueError("Duplicate unit or invalid template in structural labels")
        covered[key].add(unit)
        signatures[("template", record["template"])].add(bid)
        signatures[("a_t2_group", record["group"])].add(bid)
    sqlite_units = 0
    for bid, records in businesses.items():
        for record in records:
            path = source / "data" / bid / record["path"]
            if path.suffix.lower() in {".csv", ".xlsx"}:
                if covered[f"data/{bid}/{record['path']}"] != unit_names(path):
                    raise ValueError("Structural labels do not cover every source unit")
            elif path.suffix.lower() == ".sqlite":
                with closing(
                    sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
                ) as db:
                    tables = db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    ).fetchall()
                    if not 1 <= len(tables) <= 1024:
                        raise ValueError("SQLite catalog exceeds supported limits")
                    for (table,) in tables:
                        columns = [
                            r[1]
                            for r in db.execute(
                                f"PRAGMA table_info({identifier(table)})"
                            )
                        ]
                        signatures[("template", header_template(columns))].add(bid)
                        sqlite_units += 1
    return dict(
        input_dir=str(source),
        files=files,
        questions=membership,
        layouts=layouts,
        formats=formats,
        signatures=[
            dict(kind=k, hash=h, businesses=sorted(bs))
            for (k, h), bs in sorted(signatures.items())
        ],
        csv_xlsx_units=sum(map(len, covered.values())),
        sqlite_units=sqlite_units,
    )


def components(info: dict) -> list[list[str]]:
    parent = {b: b for b in info["layouts"]}

    def find(b):
        while parent[b] != b:
            parent[b] = parent[parent[b]]
            b = parent[b]
        return b

    for signature in info["signatures"]:
        members = signature["businesses"]
        for b in members[1:]:
            parent[find(b)] = find(members[0])
    groups = defaultdict(list)
    for b in sorted(parent):
        groups[find(b)].append(b)
    return sorted(groups.values())


def assign(info: dict, policy: dict) -> tuple[dict, list[dict]]:
    groups = components(info)
    if len(groups) < 3:
        raise ValueError("Fewer than three independent components; cannot split safely")
    seed = policy["seed"]
    groups.sort(key=lambda bs: digest([seed, bs]))
    frequency = Counter(info["layouts"].values())
    # State=(calibration count, holdout count); keep maximum metadata-only novelty.
    states = {(0, 0): (0, ())}
    for members in groups:
        novelty = max(1_000_000 // frequency[info["layouts"][b]] for b in members)
        novelty += 100_000 * (len({f for b in members for f in info["formats"][b]}) - 1)
        updated = {}
        for (cal, hold), (score, assignment) in states.items():
            for part in PARTITIONS:
                key = (
                    cal + len(members) * (part == "calibration"),
                    hold + len(members) * (part == "holdout"),
                )
                value = (score + novelty * (part == "holdout"), assignment + (part,))
                prev = updated.get(key)
                if prev is None or (-value[0], digest([seed, value[1]])) < (
                    -prev[0],
                    digest([seed, prev[1]]),
                ):
                    updated[key] = value
        states = updated
    n = len(info["layouts"])
    options = []
    for (cal, hold), (novelty, choices) in states.items():
        counts = (n - cal - hold, cal, hold)
        if min(counts) > 0:
            distance = sum(
                abs(100 * c - n * policy["ratios"][p])
                for p, c in zip(PARTITIONS, counts)
            )
            options.append(((distance, -novelty, digest([seed, choices])), choices))
    choices = min(options)[1]
    records = [
        dict(group_id=digest(bs), businesses=bs, partition=p)
        for bs, p in zip(groups, choices)
    ]
    return {b: r["partition"] for r in records for b in r["businesses"]}, records


def validate_policy(policy: dict) -> None:
    if (
        policy.get("version") != 1
        or policy.get("ratios") != dict(dev=60, calibration=20, holdout=20)
        or not isinstance(policy.get("seed"), str)
    ):
        raise ValueError("Unsupported split policy")
    if (
        policy["access"]["holdout"]["gold"]
        or policy["statistics"]["replicates_minimum"] < 1000
        or policy["statistics"]["confidence"] != 0.95
    ):
        raise ValueError("Policy weakens frozen holdout/statistical requirements")


def freeze_split(
    input_dir: Path, labels: Path, labels_sha256: str, policy_path: Path, output: Path
) -> dict:
    source, target = input_dir.resolve(strict=True), output.resolve()
    if target.exists() or not disjoint(source, target):
        raise ValueError("Output must be new and disjoint from input")
    for p in (labels, policy_path):
        if not disjoint(target, p.resolve()) or not disjoint(source, p.resolve()):
            raise ValueError("Evidence/policy must be outside input/output")
    policy_sha = sha256(policy_path)
    policy = load_json(policy_path)
    policy_bytes = policy_path.read_bytes()
    if hashlib.sha256(policy_bytes).hexdigest() != policy_sha:
        raise ValueError("Policy changed while reading")
    validate_policy(policy)
    info = catalog(input_dir, labels, labels_sha256)
    allocation, groups = assign(info, policy)
    counts = {
        p: dict(
            businesses=sum(v == p for v in allocation.values()),
            questions=sum(allocation[b] == p for b in info["questions"].values()),
            groups=sum(g["partition"] == p for g in groups),
        )
        for p in PARTITIONS
    }
    manifest = dict(
        version=1,
        builder_sha256=sha256(Path(__file__)),
        dataset_role="train",
        policy_sha256=policy_sha,
        labels_sha256=labels_sha256,
        source=info,
        groups=groups,
        business_partitions=allocation,
        summary=counts,
        gold_content_read=False,
        public_private_content_read=False,
    )
    # Check every source again before writing the lock, without opening gold.
    if (
        catalog(input_dir, labels, labels_sha256) != info
        or sha256(policy_path) != policy_sha
    ):
        raise ValueError("Input/evidence/policy changed during split creation")
    target.mkdir(parents=True, exist_ok=False)
    (target / "manifest.json").write_bytes(encoded(manifest))
    (target / "policy.json").write_bytes(policy_bytes)
    for name in ("access.jsonl", "public_submissions.jsonl", "holdout_release.jsonl"):
        (target / name).write_bytes(b"")
    expected = sha256(target / "manifest.json")
    lock = dict(
        version=1,
        manifest_sha256=expected,
        policy_sha256=policy_sha,
        frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        labels_path=str(labels.resolve()),
        policy_path=str(policy_path.resolve()),
    )
    (target / "lock.json").write_bytes(
        encoded(lock)
    )  # Written last; incomplete runs cannot open.
    return dict(
        valid=True,
        output=str(target),
        manifest_sha256=expected,
        summary=counts,
        components=len(groups),
        gold_content_read=False,
        pa="not_evaluated",
    )


def open_split(
    root: Path, expected_sha256: str, *, verify_sources=False
) -> tuple[dict, dict]:
    try:
        return _open_split(root, expected_sha256, verify_sources=verify_sources)
    except (KeyError, TypeError) as exc:
        raise ValueError("Malformed frozen split artifact") from exc


def _open_split(
    root: Path, expected_sha256: str, *, verify_sources=False
) -> tuple[dict, dict]:
    root = root.resolve(strict=True)
    lock = load_json(root / "lock.json")
    if (
        not HEX.fullmatch(expected_sha256)
        or lock["manifest_sha256"] != expected_sha256
        or sha256(root / "manifest.json") != expected_sha256
    ):
        raise ValueError("Frozen manifest hash mismatch")
    manifest = load_json(root / "manifest.json")
    policy = load_json(root / "policy.json")
    validate_policy(policy)
    if (
        sha256(root / "policy.json") != lock["policy_sha256"]
        or manifest["policy_sha256"] != lock["policy_sha256"]
    ):
        raise ValueError("Frozen policy hash mismatch")
    allocation = manifest["business_partitions"]
    covered = [b for g in manifest["groups"] for b in g["businesses"]]
    if (
        len(covered) != len(set(covered))
        or set(covered) != set(allocation)
        or set(allocation.values()) != set(PARTITIONS)
    ):
        raise ValueError("Frozen business coverage is inconsistent")
    for signature in manifest["source"]["signatures"]:
        if len({allocation[b] for b in signature["businesses"]}) != 1:
            raise ValueError("Leakage signature crosses partitions")
    if verify_sources:
        if (
            catalog(
                Path(manifest["source"]["input_dir"]),
                Path(lock["labels_path"]),
                manifest["labels_sha256"],
            )
            != manifest["source"]
            or sha256(Path(lock["policy_path"])) != lock["policy_sha256"]
        ):
            raise ValueError("Frozen source/evidence/policy has changed")
    for name in ("access.jsonl", "public_submissions.jsonl", "holdout_release.jsonl"):
        read_ledger(root / name)
    return manifest, policy


def read_ledger(path: Path) -> list[dict]:
    if (
        is_link(path)
        or not path.is_file()
        or path.stat().st_size > 8 * 1024 * 1024
        or path.stat().st_nlink > 1
    ):
        raise ValueError("Ledger missing, aliased or exceeds limit")
    events, previous = [], "0" * 64
    for line in path.read_text("utf-8").splitlines():
        try:
            obj = json_object(line)
            event_hash = obj.pop("event_sha256")
            if (
                obj["previous_sha256"] != previous
                or obj["sequence"] != len(events) + 1
                or digest(obj) != event_hash
            ):
                raise ValueError("Ledger hash chain is corrupt")
        except (KeyError, TypeError) as exc:
            raise ValueError("Ledger event is malformed") from exc
        previous = event_hash
        events.append(obj)
    return events


def append_event(root: Path, name: str, event: dict, validator=None) -> None:
    busy = root / ".ledger-operation.lock"
    try:
        fd = os.open(busy, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ValueError(
            "Ledger busy; inspect interrupted operation before retry"
        ) from exc
    try:
        os.close(fd)
        path = root / name
        events = read_ledger(path)
        if validator:
            validator(events)
        previous = digest(events[-1]) if events else "0" * 64
        record = dict(
            event,
            sequence=len(events) + 1,
            previous_sha256=previous,
            at_utc=datetime.now(timezone.utc).isoformat(),
        )
        record["event_sha256"] = digest(record)
        with path.open("ab") as handle:
            handle.write(
                json.dumps(record, ensure_ascii=False, sort_keys=True).encode() + b"\n"
            )
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        busy.unlink()


def authorize_access(
    root: Path,
    expected_sha256: str,
    partition: str,
    resource: str,
    purpose: str,
    actor: str,
    candidate_sha256: str,
) -> list[str]:
    manifest, policy = open_split(root, expected_sha256, verify_sources=True)
    if (
        partition not in PARTITIONS
        or resource not in {"questions", "gold", "context"}
        or actor not in {"developer", "evaluator", "inference"}
        or not HEX.fullmatch(candidate_sha256)
    ):
        raise ValueError("Invalid access request")
    resource_policy = "questions" if resource == "context" else resource
    allowed = purpose in policy["access"][partition][resource_policy]
    if resource == "gold" and (
        actor == "inference"
        or partition == "holdout"
        or (partition == "calibration" and actor != "evaluator")
    ):
        allowed = False
    if partition == "holdout" and actor != "inference":
        allowed = False
    append_event(
        root,
        "access.jsonl",
        dict(
            kind="authorization_only",
            partition=partition,
            resource=resource,
            purpose=purpose,
            actor=actor,
            candidate_sha256=candidate_sha256,
            manifest_sha256=expected_sha256,
            allowed=allowed,
            gold_content_read=False,
        ),
    )
    if not allowed:
        raise PermissionError(
            "Access denied by frozen split policy; holdout gold has no P0 release"
        )
    return sorted(
        qid
        for qid, b in manifest["source"]["questions"].items()
        if manifest["business_partitions"][b] == partition
    )


def log_public_submission(
    root: Path,
    expected_sha256: str,
    phase: str,
    purpose: str,
    candidate_sha256: str,
    submission_sha256: str,
    evidence: str,
) -> None:
    _, policy = open_split(root, expected_sha256, verify_sources=True)
    if (
        phase not in {"P2", "P3", "P4", "P5", "P6", "P7", "P8a", "P8b", "P9"}
        or purpose not in policy["leaderboard"]["purposes"]
        or not all(HEX.fullmatch(h) for h in (candidate_sha256, submission_sha256))
        or not evidence.strip()
        or len(evidence) > 2048
    ):
        raise ValueError("Invalid public submission audit; tuning is forbidden")

    def validate(events):
        if (
            any(e["submission_sha256"] == submission_sha256 for e in events)
            or sum(e["phase"] == phase for e in events)
            >= policy["leaderboard"]["maximum_per_phase"]
        ):
            raise ValueError("Duplicate submission or per-phase audit limit exceeded")

    append_event(
        root,
        "public_submissions.jsonl",
        dict(
            kind="public_submission_audit",
            phase=phase,
            purpose=purpose,
            candidate_sha256=candidate_sha256,
            submission_sha256=submission_sha256,
            evidence=evidence,
            manifest_sha256=expected_sha256,
        ),
        validate,
    )
