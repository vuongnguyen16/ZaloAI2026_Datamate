"""Scoped project evaluation and paired cluster bootstrap; never inference."""

import hashlib
import json
import math
import random
import time
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from datamate.artifacts import sha256, write_json
from datamate.ingest.loader import disjoint, is_link
from datamate.scoped_data import MAX_LINE, project_id, read_scoped
from datamate.scoring import parse_object, score, validate_policy
from datamate.splits import open_split


def predictions(path: Path, expected: set[str]) -> dict:
    if is_link(path) or not path.is_file() or path.stat().st_size > 128 * 1024 * 1024:
        raise ValueError("Prediction input missing, aliased or oversized")
    records = {}
    with path.open("rb") as handle:
        index = 0
        while raw := handle.readline(MAX_LINE + 1):
            index += 1
            if len(raw) > MAX_LINE or index > 10000:
                raise ValueError("Prediction resource limit")
            raw = raw.removeprefix(b"\xef\xbb\xbf") if index == 1 else raw
            try:
                qid = project_id(raw)
                obj = parse_object(raw)
            except ValueError as exc:
                raise ValueError(f"Invalid prediction JSON at line {index}") from exc
            if qid not in expected or qid in records:
                raise ValueError("Prediction ID is duplicate or outside selected scope")
            records[qid] = obj
    return records


def metric(records: list[dict]) -> dict:
    n = len(records)
    counts = Counter(r["status"] for r in records)
    return dict(
        n=n,
        correct=counts["correct"],
        wrong=counts["wrong"],
        abstain=counts["abstain"],
        pa=sum(r["score"] for r in records) / n if n else None,
    )


def breakdown(records: list[dict], field: str) -> dict:
    groups = defaultdict(list)
    for r in records:
        groups[r.get(field, "unavailable")].append(r)
    return {name: metric(rows) for name, rows in sorted(groups.items())}


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    lo, hi = math.floor(position), math.ceil(position)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)


def paired_bootstrap(
    candidate: list[dict], control: list[dict], *, replicates=1000, seed=20261105
) -> dict:
    if type(replicates) is not int or not 1000 <= replicates <= 100000:
        raise ValueError("Bootstrap requires 1000..100000 replicates")
    left = {r["id"]: r for r in candidate}
    right = {r["id"]: r for r in control}
    if (
        not left
        or len(left) != len(candidate)
        or len(right) != len(control)
        or left.keys() != right.keys()
    ):
        raise ValueError("Paired comparison requires identical unique ID coverage")
    for qid, a in left.items():
        b = right[qid]
        if any(a[k] != b[k] for k in ("business_id", "group_id")) or any(
            type(r["score"]) is not int or r["score"] not in {-1, 0, 1} for r in (a, b)
        ):
            raise ValueError("Paired comparison metadata/scores differ")
    result = {
        "replicates": replicates,
        "seed": seed,
        "confidence": 0.95,
        "delta_pa": sum(left[q]["score"] - right[q]["score"] for q in left) / len(left),
    }
    for field, offset in (("business_id", 0), ("group_id", 1)):
        grouped = defaultdict(list)
        for qid in sorted(left):
            grouped[left[qid][field]].append(left[qid]["score"] - right[qid]["score"])
        clusters = [(sum(ds), len(ds)) for _, ds in sorted(grouped.items())]
        rng = random.Random(seed + offset)
        samples = []
        for _ in range(replicates):
            draw = [clusters[rng.randrange(len(clusters))] for _ in clusters]
            samples.append(sum(s for s, _ in draw) / sum(n for _, n in draw))
        result[field] = dict(
            clusters=len(clusters),
            low=percentile(samples, 0.025),
            high=percentile(samples, 0.975),
        )
    result["small_cluster_warning"] = result["group_id"]["clusters"] < 10
    result["significance_claim_allowed"] = not result["small_cluster_warning"]
    result["internal_decision"] = (
        "insufficient_independent_clusters"
        if result["small_cluster_warning"]
        else "positive"
        if result["business_id"]["low"] > 0 and result["group_id"]["low"] > 0
        else "not_established"
    )
    return result


def output_path(output: Path, source: Path, split: Path) -> Path:
    path = output.resolve()
    if (
        path.exists()
        or not disjoint(path, source.resolve())
        or not disjoint(path, split.resolve())
    ):
        raise ValueError(
            "Evaluation output must be new and disjoint from input/frozen split"
        )
    return path


def bounded_bytes(path: Path, limit: int) -> bytes:
    if is_link(path) or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("Metadata file is missing, aliased or oversized")
    with path.open("rb") as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Metadata grew beyond its limit")
    return raw


def external_metadata(path: Path, source: Path, split: Path) -> None:
    resolved = path.resolve()
    if (
        not disjoint(resolved, source.resolve())
        or not disjoint(resolved, split.resolve())
        or is_link(path)
        or not path.is_file()
        or path.stat().st_nlink > 1
    ):
        raise ValueError(
            "Predictions/policy/metadata must be regular external files, outside raw input/frozen split"
        )


def run_eval(
    split: Path,
    manifest_sha256: str,
    partition: str,
    submission: Path,
    output: Path,
    policy_path: Path,
    *,
    control: Path | None = None,
    taxonomy: Path | None = None,
    execution: Path | None = None,
    replicates=1000,
) -> dict:
    if partition not in {"dev", "calibration"}:
        raise PermissionError("P0 evaluator cannot release holdout")
    if control and (type(replicates) is not int or not 1000 <= replicates <= 100000):
        raise ValueError("Bootstrap requires 1000..100000 replicates")
    manifest, split_policy = open_split(split, manifest_sha256, verify_sources=True)
    source = Path(manifest["source"]["input_dir"])
    target = output_path(output, source, split)
    for path in (submission, control, policy_path, taxonomy, execution):
        if path is not None:
            external_metadata(path, source, split)
    policy_bytes = bounded_bytes(policy_path, 1024 * 1024)
    if len(policy_bytes) > 1024 * 1024 or is_link(policy_path):
        raise ValueError("Scoring policy is aliased or oversized")
    policy = parse_object(policy_bytes)
    validate_policy(policy)
    policy_sha = hashlib.sha256(policy_bytes).hexdigest()
    expected = {
        q
        for q, b in manifest["source"]["questions"].items()
        if manifest["business_partitions"][b] == partition
    }
    frozen_hashes = {"submission": sha256(submission), "policy": policy_sha}
    actual = predictions(submission, expected)
    if control:
        frozen_hashes["control"] = sha256(control)
    other = predictions(control, expected) if control else None
    metadata = {}
    metadata_hashes = {}
    if taxonomy:
        if partition != "dev":
            raise PermissionError("Detailed taxonomy cannot be used for calibration")
        obj = parse_object(bounded_bytes(taxonomy, 16 * 1024 * 1024))
        if obj["manifest_sha256"] != manifest_sha256 or obj["partition"] != partition:
            raise ValueError("Taxonomy provenance differs")
        metadata = {r["id"]: r for r in obj["records"]}
        if (
            set(metadata) != expected
            or len(metadata) != len(obj["records"])
            or any(not isinstance(r.get("family"), str) for r in metadata.values())
        ):
            raise ValueError("Taxonomy coverage differs")
        metadata_hashes["taxonomy"] = sha256(taxonomy)
    events = {}
    if execution:
        if is_link(execution) or execution.stat().st_size > 32 * 1024 * 1024:
            raise ValueError("Execution evidence oversized or aliased")
        for raw in bounded_bytes(execution, 32 * 1024 * 1024).splitlines():
            e = parse_object(raw)
            qid = e.get("id", e.get("question_id"))
            duration = e.get("duration_seconds")
            if (
                not isinstance(qid, str)
                or qid not in expected
                or qid in events
                or type(duration) not in (int, float, Decimal)
                or not math.isfinite(duration)
                or duration < 0
                or not isinstance(e.get("route"), str)
            ):
                raise ValueError("Invalid execution evidence")
            e["duration_seconds"] = float(duration)
            events[qid] = e
        metadata_hashes["execution"] = sha256(execution)
    start = time.perf_counter()
    reference, audit = read_scoped(
        split,
        manifest_sha256,
        partition,
        "gold",
        "evaluation",
        "evaluator",
        frozen_hashes["submission"],
    )
    group = {b: g["group_id"] for g in manifest["groups"] for b in g["businesses"]}

    def evaluate(preds):
        return [
            dict(
                id=q,
                business_id=manifest["source"]["questions"][q],
                group_id=group[manifest["source"]["questions"][q]],
                expected_type=reference[q]["type"],
                family=metadata.get(q, {}).get("family", "unavailable"),
                route=events.get(q, {}).get("route", "unavailable"),
                **score(reference[q], preds.get(q)),
            )
            for q in sorted(expected)
        ]

    rows = evaluate(actual)
    result = dict(
        valid=True,
        scope="project_scorer_from_written_rules; not organizer executable or model baseline",
        implementation_sha256={
            n: sha256(Path(__file__).with_name(n))
            for n in ("evaluation.py", "scoring.py", "scoped_data.py")
        },
        partition=partition,
        manifest_sha256=manifest_sha256,
        scoring_policy_sha256=policy_sha,
        policy_provisional=policy["provisional"],
        candidate_sha256=frozen_hashes["submission"],
        summary=metric(rows),
        by_type=breakdown(rows, "expected_type"),
        by_business=breakdown(rows, "business_id"),
        by_family=breakdown(rows, "family"),
        by_route=breakdown(rows, "route"),
        reader_audit=audit,
        runtime=dict(
            inference_available=len(events) == len(expected),
            observed_records=len(events),
            inference_seconds=sum(e["duration_seconds"] for e in events.values())
            if len(events) == len(expected)
            else None,
            evaluator_seconds=time.perf_counter() - start,
        ),
        gold_answers_exported=False,
        holdout_answer_values_decoded=False,
        metadata_sha256=metadata_hashes,
    )
    if other is not None:
        control_rows = evaluate(other)
        result["control_summary"] = metric(control_rows)
        result["comparison"] = paired_bootstrap(
            rows,
            control_rows,
            replicates=replicates,
            seed=split_policy["statistics"]["seed"],
        )
        result["new_errors_count"] = sum(
            r["score"] < c["score"] for r, c in zip(rows, control_rows)
        )
        if partition == "dev":
            result["new_error_ids"] = [
                r["id"] for r, c in zip(rows, control_rows) if r["score"] < c["score"]
            ]
    for name, path in (
        ("submission", submission),
        ("policy", policy_path),
        ("control", control),
    ):
        if path and sha256(path) != frozen_hashes[name]:
            raise ValueError("Evaluation input changed after candidate freeze")
    for name, path in (("taxonomy", taxonomy), ("execution", execution)):
        if path and sha256(path) != metadata_hashes[name]:
            raise ValueError("Evaluation metadata changed during scoring")
    open_split(split, manifest_sha256, verify_sources=True)
    result["runtime"]["evaluator_seconds"] = time.perf_counter() - start
    target.mkdir(parents=True, exist_ok=False)
    write_json(target / "evaluation.json", result)
    if partition == "dev":
        (target / "per_question.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
            encoding="utf-8",
        )
    return result
