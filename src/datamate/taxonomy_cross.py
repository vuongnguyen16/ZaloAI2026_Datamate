"""Cross the frozen P0 dev taxonomy without reopening any reference file."""

import hashlib
from collections import Counter
from itertools import product
from pathlib import Path

from datamate.artifacts import sha256, write_json
from datamate.evaluation import external_metadata, output_path
from datamate.prediction_store import regular_bytes, safe_path
from datamate.scoring import TYPES, parse_object
from datamate.splits import authorize_access, open_split

ROOT = Path(__file__).resolve().parents[2]
FIELDS = {
    "id",
    "business_id",
    "expected_type",
    "family",
    "family_candidates",
    "ambiguous_family",
    "operations",
    "time_forms",
    "abbreviations",
    "ascii_only",
    "question_sha256",
}


def cross_table(records: list[dict]) -> dict:
    cells, seen = Counter(), set()
    if not records or len(records) > 10000:
        raise ValueError("taxonomy record count exceeds bounds")
    for row in records:
        if not isinstance(row.get("id"), str) or row["id"] in seen:
            raise ValueError("duplicate or invalid taxonomy ID")
        seen.add(row["id"])
        family, kind = row["family"], row["expected_type"]
        if (
            kind not in TYPES
            or not isinstance(family, str)
            or not 0 < len(family) <= 64
        ):
            raise ValueError("invalid taxonomy label")
        for field in ("operations", "time_forms"):
            values = row[field]
            if (
                not isinstance(values, list)
                or not 0 < len(values) <= 64
                or not all(isinstance(v, str) and 0 < len(v) <= 64 for v in values)
            ):
                raise ValueError("invalid bounded taxonomy labels")
        for operation, time_form in product(
            set(row["operations"]), set(row["time_forms"])
        ):
            cells[family, operation, kind, time_form] += 1
    return {
        "unique_questions": len(seen),
        "memberships": sum(cells.values()),
        "counting": "one question per cell; Cartesian multi-label memberships may exceed unique questions",
        "cells": [
            dict(family=f, operation=o, expected_type=t, time_form=d, count=n)
            for (f, o, t, d), n in sorted(cells.items())
        ],
    }


def run_taxonomy_cross(
    split: Path, manifest_sha256: str, output: Path, proof=None
) -> dict:
    manifest, _ = open_split(split, manifest_sha256, verify_sources=True)
    source = Path(manifest["source"]["input_dir"])
    target = safe_path(output_path(output, source, split))
    if proof is None:
        proof = parse_object(
            regular_bytes(ROOT / "manifests/p0_evidence.json", 1024 * 1024)
        )
    else:
        # The override is fixture-only. It cannot turn a copied gold file into trusted
        # metadata for the real split; production has one committed hash allowlist.
        if not all(
            q.startswith("synthetic_") for q in manifest["source"]["questions"]
        ) or not all(
            b.startswith("synthetic_") for b in manifest["business_partitions"]
        ):
            raise ValueError("proof override is restricted to synthetic fixtures")
    if proof.get("split_manifest_sha256") != manifest_sha256:
        raise ValueError("taxonomy proof split mismatch")
    candidates = [
        a for a in proof["artifacts"] if Path(a["path"]).name == "taxonomy.json"
    ]
    if len(candidates) != 1:
        raise ValueError("proof requires exactly one pinned taxonomy artifact")
    pinned = candidates[0]
    allowed = set(
        authorize_access(
            split,
            manifest_sha256,
            "dev",
            "context",
            "taxonomy",
            "developer",
            pinned["sha256"],
        )
    )
    path = safe_path(ROOT / pinned["path"])
    external_metadata(path, source, split)
    raw = regular_bytes(path, 32 * 1024 * 1024, single_link=True)
    if hashlib.sha256(raw).hexdigest() != pinned["sha256"]:
        raise ValueError("pinned taxonomy hash mismatch before decode")
    taxonomy = parse_object(raw)
    rules = proof["taxonomy_rules"]
    rule_path = safe_path(ROOT / rules["path"])
    external_metadata(rule_path, source, split)
    if (
        taxonomy.get("valid") is not True
        or taxonomy.get("partition") != "dev"
        or taxonomy.get("manifest_sha256") != manifest_sha256
        or taxonomy.get("rules_sha256") != rules["sha256"]
        or sha256(rule_path) != rules["sha256"]
        or taxonomy.get("implementation_sha256")
        != sha256(ROOT / "src/datamate/taxonomy.py")
    ):
        raise ValueError("taxonomy source/provenance mismatch")
    records = taxonomy.get("records")
    if not isinstance(records, list) or len(records) != len(allowed):
        raise ValueError("taxonomy coverage mismatch")
    ids = set()
    for row in records:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError("unexpected taxonomy fields; no gold answers allowed")
        qid = row["id"]
        if (
            qid not in allowed
            or qid in ids
            or manifest["source"]["questions"][qid] != row["business_id"]
        ):
            raise ValueError("taxonomy duplicate/out-of-scope/membership mismatch")
        ids.add(qid)
    cross = cross_table(records)
    result = {
        "valid": True,
        "partition": "dev",
        "manifest_sha256": manifest_sha256,
        "taxonomy_sha256": pinned["sha256"],
        "taxonomy_path": str(path),
        "label_method": "P0 primary family/operation/time heuristic; expected_type from authorized dev taxonomy",
        "gold_content_read": False,
        "calibration_answer_values_decoded": False,
        "holdout_answer_values_decoded": False,
        "gold_answers_exported": False,
        **cross,
    }
    target.mkdir(parents=True, exist_ok=False)
    write_json(target / "cross.json", result)
    lines = [
        "# Bảng chéo taxonomy dev P0",
        "",
        f"Câu unique: {cross['unique_questions']}; memberships: {cross['memberships']}.",
        "Nhãn heuristic; tổng ô không phải tổng số câu. Không mở lại gold.",
        "",
        "| Family | Operation | Type | Time | Count |",
        "|---|---|---|---|---:|",
    ]
    lines += [
        f"| {c['family']} | {c['operation']} | {c['expected_type']} | {c['time_form']} | {c['count']} |"
        for c in cross["cells"]
    ]
    (target / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    # CLI never dumps cells/IDs into a transcript or exported tracker.
    return {k: v for k, v in result.items() if k != "cells"} | {
        "cell_count": len(cross["cells"]),
        "output": str(target),
    }
