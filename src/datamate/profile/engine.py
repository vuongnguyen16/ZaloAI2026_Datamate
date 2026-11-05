"""Read-only raw profiling; all source strings remain data, never instructions."""

import hashlib
import json
import platform
import re
import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path

import duckdb

from datamate.artifacts import sha256, write_json
from datamate.ingest import IngestError, LoaderOptions, loader
from datamate.ingest.readers import dump
from datamate.profile.model import ProfileOptions
from datamate.profile.stats import ColumnStats, Retention, preview
from datamate.profile.structure import VERSION as STRUCTURE_VERSION
from datamate.profile.structure import detect
from datamate.profile.text_quality import TextQuality

VERSION = 1
SCOPE = (
    "A-T2 raw profile, format evidence and conservative structure; no cleaning/model"
)


def code_hash():
    return hashlib.sha256(
        dump(
            {p.name: sha256(p) for p in sorted(Path(__file__).parent.glob("*.py"))}
        ).encode()
    ).hexdigest()


def read_json(path, limit=64 * 1024 * 1024):
    if loader.is_link(path) or not path.is_file() or path.stat().st_size > limit:
        raise IngestError(
            "profile_artifact",
            "Profile input artifact is missing, aliased or oversized",
        )
    return json.loads(path.read_text("utf-8"))


def header_selections(path):
    if path is None:
        return {}, None
    record = read_json(path, 8 * 1024 * 1024)
    if (
        not isinstance(record, dict)
        or set(record) != {"version", "selections"}
        or type(record["version"]) is not int
        or record["version"] != VERSION
        or not isinstance(record["selections"], list)
    ):
        raise IngestError(
            "profile_header_map", "Unsupported explicit header map schema"
        )
    selections = {}
    for entry in record["selections"]:
        required = {
            "business_id",
            "ingest_fingerprint",
            "source_file",
            "source_name",
            "source_kind",
            "rows",
        }
        if (
            not isinstance(entry, dict)
            or not required <= set(entry)
            or set(entry) - required - {"data_start_row"}
        ):
            raise IngestError("profile_header_map", "Invalid explicit header entry")
        if any(
            not isinstance(entry[k], str)
            for k in entry
            if k not in {"rows", "data_start_row"}
        ):
            raise IngestError(
                "profile_header_map", "Header identity fields must be strings"
            )
        rows = entry["rows"]
        if (
            not isinstance(rows, list)
            or not 0 <= len(rows) <= 64
            or not rows
            and "data_start_row" not in entry
            or any(type(r) is not int or r < 1 for r in rows)
            or rows != sorted(set(rows))
            or not re.fullmatch(r"[0-9a-f]{64}", entry["ingest_fingerprint"])
            or entry["source_kind"] not in {"csv", "xlsx_sheet"}
            or "data_start_row" in entry
            and (
                type(entry["data_start_row"]) is not int
                or entry["data_start_row"] <= max(rows, default=0)
            )
        ):
            raise IngestError(
                "profile_header_map", "Invalid header rows/fingerprint/source kind"
            )
        key = (
            entry["business_id"],
            entry["source_file"],
            entry["source_name"],
            entry["source_kind"],
        )
        if key in selections:
            raise IngestError("profile_header_map", "Duplicate explicit header entry")
        selections[key] = entry
    return selections, sha256(path)


def cell_type(kind, metadata, position):
    if kind == "csv":
        return "csv:text"
    codes = metadata.get("types")
    allowed = "nisxbed" if kind == "xlsx_sheet" else "irtb0"
    if (
        not isinstance(codes, str)
        or position > len(codes)
        or codes[position - 1] not in allowed
    ):
        raise IngestError("profile_payload", "Invalid physical type metadata")
    return ("xlsx:" if kind == "xlsx_sheet" else "sqlite:") + codes[position - 1]


def profile_unit(con, unit, options, selection, cells_budget):
    width = unit["max_width"]
    if type(width) is not int or not 0 <= width <= options.max_columns:
        raise IngestError("profile_column_limit", "Unit width exceeds profile limit")
    kind = unit["source_kind"]
    if kind not in {"csv", "xlsx_sheet", "sqlite_table"}:
        raise IngestError("profile_payload", "Unsupported unit kind")
    retention = Retention(options.max_retained_bytes_per_unit)
    columns = [ColumnStats(i, options, retention) for i in range(1, width + 1)]
    count = nonempty = previous = max_width = 0
    digest = hashlib.sha256()
    first_rows, selected_rows = [], {}
    prefix, prefix_bytes, evidence_limited = [], 0, False
    quality = TextQuality()
    chosen = set(selection["rows"]) if selection else set()
    cursor = con.execute(
        f"SELECT __row,__width,CAST(__payload AS VARCHAR) FROM {loader.identifier(unit['storage_table'])} ORDER BY __row"
    )
    while batch := cursor.fetchmany(64):
        for number, row_width, payload in batch:
            count += 1
            if count > options.max_rows_per_unit:
                raise IngestError("profile_row_limit", "Unit exceeds profile row limit")
            if (
                type(number) is not int
                or number <= previous
                or type(row_width) is not int
                or not 0 <= row_width <= width
            ):
                raise IngestError("profile_payload", "Invalid raw row coordinates")
            previous, max_width = number, max(max_width, row_width)
            parsed = json.loads(payload)
            if (
                not isinstance(parsed, dict)
                or set(parsed) != {"v", "m"}
                or not isinstance(parsed["v"], dict)
                or not isinstance(parsed["m"], dict)
            ):
                raise IngestError("profile_payload", "Invalid raw frame structure")
            values, meta = parsed["v"], parsed["m"]
            if count <= options.header_scan_rows:
                prefix_bytes += len(payload.encode("utf-8"))
                if prefix_bytes <= options.header_scan_bytes:
                    prefix.append({"row": number, "width": row_width, **parsed})
                else:
                    evidence_limited = True
            cells_budget[0] += len(values)
            if cells_budget[0] > options.max_cells_per_business:
                raise IngestError(
                    "profile_cell_limit", "Business exceeds profile cell limit"
                )
            if kind == "csv":
                if set(values) != {str(i) for i in range(1, row_width + 1)}:
                    raise IngestError(
                        "profile_payload", "CSV record width differs from cells"
                    )
                location = {k: meta[k] for k in ("line_start", "line_end")}
            else:
                location = {}
                if len(meta.get("types", "")) != row_width:
                    raise IngestError(
                        "profile_payload", "Raw width differs from type metadata"
                    )
                if kind == "sqlite_table" and (
                    row_width != width or len(values) != width
                ):
                    raise IngestError(
                        "profile_payload", "SQLite row differs from declared schema"
                    )
                if kind == "xlsx_sheet" and {
                    str(i) for i, t in enumerate(meta["types"], 1) if t != "-"
                } != set(values):
                    raise IngestError(
                        "profile_payload",
                        "Sparse worksheet cells differ from type metadata",
                    )
            preview_cells = {}
            capture = len(first_rows) < options.preview_rows or number in chosen
            for key, value in values.items():
                if (
                    not re.fullmatch(r"[1-9][0-9]*", key)
                    or not 1 <= int(key) <= row_width
                    or (value is not None and not isinstance(value, str))
                ):
                    raise IngestError(
                        "profile_payload", "Invalid raw cell position/value"
                    )
                i = int(key)
                typ = cell_type(kind, meta, i)
                columns[i - 1].add(value, typ, number, location)
                if typ in {
                    "csv:text",
                    "xlsx:i",
                    "xlsx:s",
                    "xlsx:x",
                    "xlsx:d",
                    "sqlite:t",
                }:
                    quality.add(value, number, i)
                if capture and (i <= options.preview_columns or number in chosen):
                    preview_cells[key] = {
                        "physical_type": typ,
                        **preview(value, options.value_bytes),
                    }
            if capture:
                evidence = {
                    "source_row": number,
                    "width": row_width,
                    **location,
                    "cells": preview_cells,
                    "omitted_cells": len(values) - len(preview_cells),
                }
                if len(first_rows) < options.preview_rows:
                    # Header annotation may be wide; the generic first-row preview stays bounded.
                    first_rows.append(
                        {
                            **evidence,
                            "cells": {
                                k: v
                                for k, v in preview_cells.items()
                                if int(k) <= options.preview_columns
                            },
                            "omitted_cells": sum(
                                int(k) > options.preview_columns for k in values
                            ),
                        }
                    )
                if number in chosen:
                    selected_rows[number] = evidence
            nonempty += any(v is not None and v != "" for v in values.values())
            loader.frame_update(digest, number, row_width, payload)
    if (
        count != unit["row_count"]
        or nonempty != unit["nonempty_rows"]
        or digest.hexdigest() != unit["frame_sha256"]
    ):
        raise IngestError(
            "profile_integrity", "Raw frame digest/counts differ from manifest"
        )
    if kind != "sqlite_table" and max_width != width:
        raise IngestError("profile_integrity", "Raw max width differs from manifest")
    if chosen != set(selected_rows):
        raise IngestError(
            "profile_header_rows", "An explicit header row does not exist in source"
        )
    if kind == "sqlite_table":
        structure = {
            "status": "source_schema",
            "header_rows": [],
            "data_start_row": 1 if count else None,
            "rule_version": STRUCTURE_VERSION,
            "reason": "declared_sqlite_schema",
        }
    elif selection:
        data_start = selection.get("data_start_row")
        if data_start is None:
            data_start = con.execute(
                f"SELECT min(__row) FROM {loader.identifier(unit['storage_table'])} WHERE __row>? AND EXISTS(SELECT 1 FROM json_each(json_extract(__payload,'$.v')) j WHERE json_extract_string(j.value,'$') IS NOT NULL AND json_extract_string(j.value,'$')<>'')",
                [max(chosen, default=0)],
            ).fetchone()[0]
        if (
            data_start is not None
            and con.execute(
                f"SELECT count(*) FROM {loader.identifier(unit['storage_table'])} WHERE __row=?",
                [data_start],
            ).fetchone()[0]
            != 1
        ):
            raise IngestError(
                "profile_header_rows", "Explicit data_start_row is absent from source"
            )
        structure = {
            "status": "explicit_annotation" if chosen else "no_header",
            "header_rows": sorted(chosen),
            "data_start_row": data_start,
            "rule_version": STRUCTURE_VERSION,
            "reason": "source_bound_annotation",
        }
    elif options.detect_headers:
        effective_width = max(
            (int(k) for r in prefix for k, v in r["v"].items() if v not in (None, "")),
            default=0,
        )
        structure = detect(
            prefix,
            effective_width,
            complete_empty=count == 0,
            evidence_limited=evidence_limited,
        )
        chosen = set(structure["header_rows"])
        for r in prefix:
            if r["row"] in chosen:
                selected_rows[r["row"]] = {
                    "source_row": r["row"],
                    "width": r["width"],
                    **{
                        k: v
                        for k, v in r["m"].items()
                        if k in {"line_start", "line_end"}
                    },
                    "cells": {
                        k: {
                            "physical_type": cell_type(kind, r["m"], int(k)),
                            **preview(v, options.value_bytes),
                        }
                        for k, v in r["v"].items()
                    },
                    "omitted_cells": 0,
                }
    else:
        structure = {
            "status": "unresolved",
            "header_rows": [],
            "data_start_row": None,
            "rule_version": STRUCTURE_VERSION,
            "reason": "automatic_selection_disabled",
        }
    result_columns = [column.finish(count) for column in columns]
    if kind == "sqlite_table":
        declared = unit["metadata"]["columns"]
        if len(declared) != width:
            raise IngestError(
                "profile_payload", "SQLite declared width differs from cached width"
            )
        for c, declaration in zip(result_columns, declared, strict=True):
            c["declared_name"], c["declared_type"] = declaration[1:3]
    for c in result_columns:
        c["header_cells"] = [
            {"source_row": r, "cell": selected_rows[r]["cells"].get(str(c["position"]))}
            for r in sorted(chosen)
        ]
        c["data_samples"] = []
    sample_rows = 0
    if structure["data_start_row"] is not None:
        seen_samples = [set() for _ in columns]
        for number, payload in con.execute(
            f"SELECT __row,CAST(__payload AS VARCHAR) FROM {loader.identifier(unit['storage_table'])} WHERE __row>=? ORDER BY __row LIMIT ?",
            [structure["data_start_row"], options.data_sample_rows],
        ).fetchall():
            sample_rows += 1
            parsed = json.loads(payload)
            for key, value in parsed["v"].items():
                i = int(key) - 1
                if (
                    value is None
                    or value == ""
                    or len(result_columns[i]["data_samples"])
                    >= options.samples_per_column
                ):
                    continue
                token = hashlib.sha256(value.encode("utf-8")).hexdigest()
                if token not in seen_samples[i]:
                    seen_samples[i].add(token)
                    result_columns[i]["data_samples"].append(
                        {
                            "source_row": number,
                            **{
                                k: v
                                for k, v in parsed["m"].items()
                                if k in {"line_start", "line_end"}
                            },
                            **preview(value, options.value_bytes),
                        }
                    )
    return {
        **{
            k: unit[k]
            for k in (
                "source_file",
                "source_name",
                "source_kind",
                "storage_table",
                "view_name",
            )
        },
        "row_count": count,
        "nonempty_rows": nonempty,
        "max_width": width,
        "frame_sha256": digest.hexdigest(),
        "statistics_scope": "all physical raw rows, including headers/totals/duplicates/blanks",
        "header": {
            "status": structure["status"],
            "rows": sorted(chosen),
            "selected_row_evidence": [selected_rows[r] for r in sorted(chosen)],
            "data_start_row": structure["data_start_row"],
            "automatic_detection": structure["status"] == "auto_rule",
            "rows_filtered_from_statistics": False,
        },
        "source_structure": unit["metadata"],
        "row_preview": first_rows,
        "structure": structure,
        "text_quality": quality.record(),
        "data_samples_scope": {
            "from_row": structure["data_start_row"],
            "rows_scanned": sample_rows,
            "max_rows": options.data_sample_rows,
            "totals_notes_duplicates_still_present": True,
        },
        "columns": result_columns,
    }


def schema_descriptor(profile):
    """Machine-readable baseline input; no prompt or semantic interpretation."""
    return {
        "version": VERSION,
        "scope": SCOPE,
        "business_id": profile["business_id"],
        "ingest_fingerprint": profile["provenance"]["ingest_fingerprint"],
        "database": profile["provenance"]["database"],
        "source_strings_are_untrusted_data": True,
        "tables": [
            {
                "sql_name": u["view_name"],
                "source_file": u["source_file"],
                "source_name": u["source_name"],
                "source_kind": u["source_kind"],
                "row_count": u["row_count"],
                "row_coordinate_column": "__row",
                "header_status": u["header"]["status"],
                "header_rows": u["header"]["rows"],
                "data_start_row": u["header"]["data_start_row"],
                "structure": u["structure"],
                "row_preview": u["row_preview"]
                if u["header"]["status"] == "unresolved"
                else [],
                "format": {
                    k: v
                    for k, v in profile["provenance"]["source_metadata"]
                    .get(u["source_file"], {})
                    .items()
                    if k
                    in {
                        "encoding",
                        "encoding_status",
                        "bom",
                        "delimiter",
                        "delimiter_status",
                        "format_policy_version",
                        "format",
                        "workbook_properties",
                        "row_order",
                        "sqlite_version",
                    }
                },
                "text_quality": u["text_quality"],
                "data_samples_scope": u["data_samples_scope"],
                "columns": [
                    {
                        k: c[k]
                        for k in (
                            "position",
                            "sql_name",
                            "sql_type",
                            "physical_types",
                            "samples",
                            "data_samples",
                            "header_cells",
                            "declared_name",
                            "declared_type",
                        )
                        if k in c
                    }
                    for c in u["columns"]
                ],
            }
            for u in profile["units"]
        ],
        "limitations": [
            "Raw rows include headers/totals/duplicates; VARCHAR values are not normalized",
            "Conservative header rule can abstain; no legacy text repair, semantic types, joins or model validation",
        ],
    }


def profile_business(
    source, cache, business, options, selections, annotation_hash, profile_code
):
    bid = business["business_id"]
    raw = loader.business_path(source, bid)
    fingerprint = business["fingerprint"]
    if not isinstance(fingerprint, str) or not re.fullmatch(
        r"[0-9a-f]{64}", fingerprint
    ):
        raise IngestError("profile_artifact", "Invalid ingestion fingerprint")
    generation = (
        cache / ("b_" + hashlib.sha256(bid.encode()).hexdigest()[:24]) / fingerprint
    )
    if loader.is_link(generation.parent) or not generation.resolve().is_relative_to(
        cache
    ):
        raise IngestError("profile_artifact", "Aliased cache generation")
    manifest_path, database = generation / "manifest.json", generation / "raw.duckdb"
    if (
        Path(business["database"]).resolve() != database.resolve()
        or Path(business["manifest"]).resolve() != manifest_path.resolve()
    ):
        raise IngestError(
            "profile_artifact",
            "Report cache identity does not match business fingerprint",
        )
    manifest = read_json(manifest_path)
    manifest_hash = sha256(manifest_path)
    signature = manifest["signature"]
    if (
        signature["business_id"] != bid
        or signature["loader_code_sha256"] != loader.code_hash()
        or signature["duckdb_version"] != duckdb.__version__
        or signature["python_version"] != platform.python_version()
        or hashlib.sha256(dump(signature).encode()).hexdigest() != fingerprint
    ):
        raise IngestError(
            "profile_stale_ingest",
            "Raw generation requires re-ingestion for current inputs/runtime/code",
        )
    manifest = loader.validate_cache(generation, signature, fingerprint)
    loader_options = LoaderOptions(**signature["options"])
    if loader.snapshot(raw, loader_options) != signature["files"]:
        raise IngestError(
            "profile_stale_ingest", "Raw source differs from ingestion generation"
        )
    units = manifest["units"]
    if units != business["units"] or len(units) > options.max_units:
        raise IngestError(
            "profile_unit_limit",
            "Report units differ from manifest or exceed profile limit",
        )
    keys = {(bid, u["source_file"], u["source_name"], u["source_kind"]) for u in units}
    explicit = {k: v for k, v in selections.items() if k[0] == bid}
    if set(explicit) - keys or any(
        e["ingest_fingerprint"] != fingerprint for e in explicit.values()
    ):
        raise IngestError(
            "profile_header_map",
            "Explicit header map references an unknown or stale source",
        )
    profiles, cells_budget = [], [0]
    with loader.connect(database, read_only=True) as con:
        readme_quality = TextQuality()
        for row, text in enumerate(
            con.execute("SELECT text FROM __dm_readme").fetchone()[0].split("\n"), 1
        ):
            readme_quality.add(text, row, None)
        for unit in units:
            try:
                profiles.append(
                    profile_unit(
                        con,
                        unit,
                        options,
                        explicit.get(
                            (
                                bid,
                                unit["source_file"],
                                unit["source_name"],
                                unit["source_kind"],
                            )
                        ),
                        cells_budget,
                    )
                )
            except IngestError as exc:
                exc.location.update(
                    source_file=unit["source_file"], unit=unit["source_name"]
                )
                raise
    if (
        loader.snapshot(raw, loader_options) != signature["files"]
        or sha256(database) != manifest["database_sha256"]
        or sha256(manifest_path) != manifest_hash
        or code_hash() != profile_code
    ):
        raise IngestError(
            "profile_input_changed", "Raw/cache/profile code changed during profiling"
        )
    return {
        "version": VERSION,
        "scope": SCOPE,
        "business_id": bid,
        "options": asdict(options),
        "provenance": {
            "ingest_fingerprint": fingerprint,
            "database": str(database),
            "database_sha256": manifest["database_sha256"],
            "manifest_sha256": manifest_hash,
            "profile_code_sha256": profile_code,
            "header_map_sha256": annotation_hash,
            "files": signature["files"],
            "source_metadata": manifest["source_metadata"],
        },
        "units": profiles,
        "readme_text_quality": readme_quality.record(),
        "summary": {
            "units": len(profiles),
            "columns": sum(u["max_width"] for u in profiles),
            "rows": sum(u["row_count"] for u in profiles),
            "present_cells": cells_budget[0],
            "headers_unresolved": sum(
                u["header"]["status"] == "unresolved" for u in profiles
            ),
            "headers_auto": sum(u["header"]["status"] == "auto_rule" for u in profiles),
        },
        "gold_content_read": False,
        "model": "not_run",
        "pa": "not_evaluated",
    }


def publish_business(output, profile, options, before_publish):
    token = "b_" + hashlib.sha256(profile["business_id"].encode()).hexdigest()[:24]
    parent = output / "businesses"
    parent.mkdir(exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".building-", dir=parent))
    try:
        for name, value in [
            ("profile.json", profile),
            ("schema.json", schema_descriptor(profile)),
        ]:
            content = (
                json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
            )
            if len(content.encode("utf-8")) > options.max_report_bytes_per_business:
                raise IngestError(
                    "profile_report_limit",
                    "Business profile/schema exceeds output byte limit",
                )
            (stage / name).write_text(content, encoding="utf-8")
        before_publish()
        target = parent / token
        stage.rename(target)
        return {
            "valid": True,
            "business_id": profile["business_id"],
            "summary": profile["summary"],
            **{
                name: {
                    "path": str(target / (name + ".json")),
                    "sha256": sha256(target / (name + ".json")),
                }
                for name in ("profile", "schema")
            },
        }
    finally:
        if (
            stage.exists()
            and stage.resolve().parent == parent.resolve()
            and not loader.is_link(stage)
        ):
            shutil.rmtree(stage)


def _run_profile(input_dir, ingest_report, output_dir, options, header_map):
    source = Path(input_dir).resolve(strict=True)
    report_path = Path(ingest_report).resolve(strict=True)
    output = Path(output_dir).resolve()
    header_path = Path(header_map).resolve(strict=True) if header_map else None
    # Refuse a wrong input path before parsing any split file (including gold).
    if report_path.name != "ingest.json" or not loader.disjoint(source, report_path):
        raise IngestError(
            "profile_artifact", "Expected an external ingest.json artifact"
        )
    if header_path is not None and not loader.disjoint(source, header_path):
        raise IngestError(
            "profile_header_map", "Header annotation must be outside raw input"
        )
    report = read_json(report_path)
    report_hash = sha256(report_path)
    if (
        not isinstance(report, dict)
        or not report.get("valid")
        or report.get("scope") != "A-T1 raw ingestion; no cleaning/gold/model"
    ):
        raise IngestError(
            "profile_artifact", "Expected a successful A-T1 ingestion report"
        )
    _, cache = loader.roots(source, Path(report["cache_root"]))
    protected = [source, cache, report_path.parent] + (
        [header_path] if header_path else []
    )
    if output.exists() or any(not loader.disjoint(output, p) for p in protected):
        raise IngestError(
            "output_overlap",
            "Profile output must be new and disjoint from all inputs/cache",
        )
    ids = [b["business_id"] for b in report["businesses"]]
    if not ids or len(ids) != len(set(ids)):
        raise IngestError(
            "profile_artifact", "Empty or duplicate ingestion business list"
        )
    selections, annotation_hash = header_selections(header_path)
    if {k[0] for k in selections} - set(ids):
        raise IngestError(
            "profile_header_map",
            "Header map references a business outside the ingest report",
        )
    profile_code = code_hash()
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for business in sorted(report["businesses"], key=lambda b: b["business_id"]):
        try:
            profile = profile_business(
                source,
                cache,
                business,
                options,
                selections,
                annotation_hash,
                profile_code,
            )

            def before_publish():
                provenance = profile["provenance"]
                manifest_path = Path(business["manifest"])
                signature = read_json(manifest_path)["signature"]
                if (
                    sha256(report_path) != report_hash
                    or (header_path and sha256(header_path) != annotation_hash)
                    or code_hash() != profile_code
                    or sha256(manifest_path) != provenance["manifest_sha256"]
                    or sha256(Path(business["database"]))
                    != provenance["database_sha256"]
                    or loader.snapshot(
                        loader.business_path(source, business["business_id"]),
                        LoaderOptions(**signature["options"]),
                    )
                    != provenance["files"]
                ):
                    raise IngestError(
                        "profile_input_changed",
                        "Profile inputs changed before publication",
                    )

            results.append(publish_business(output, profile, options, before_publish))
        except IngestError as exc:
            results.append(
                {
                    "valid": False,
                    "business_id": business["business_id"],
                    "errors": [exc.record()],
                }
            )
        except (OSError, ValueError, KeyError, TypeError, IndexError, duckdb.Error):
            error = IngestError("profile_failed", "Business raw profiling failed")
            results.append(
                {
                    "valid": False,
                    "business_id": business["business_id"],
                    "errors": [error.record()],
                }
            )
    result = {
        "version": VERSION,
        "valid": all(b["valid"] for b in results),
        "scope": SCOPE,
        "ingest_report": str(report_path),
        "ingest_report_sha256": report_hash,
        "profile_code_sha256": profile_code,
        "options": asdict(options),
        "header_map_sha256": annotation_hash,
        "businesses": results,
        "summary": {
            "businesses": len(results),
            "successful": sum(b["valid"] for b in results),
            **{
                k: sum(b.get("summary", {}).get(k, 0) for b in results)
                for k in (
                    "units",
                    "columns",
                    "rows",
                    "present_cells",
                    "headers_unresolved",
                    "headers_auto",
                )
            },
        },
        "deferred": [
            "legacy-font converter without verified real examples",
            "multi-table region discovery and semantic inference",
            "actual model/prompt/PA integration owned by D-E-T2",
        ],
        "gold_content_read": False,
        "model": "not_run",
        "pa": "not_evaluated",
    }
    write_json(output / "profile.json", result)
    return result


def run_profile(input_dir, ingest_report, output_dir, options=None, header_map=None):
    try:
        return _run_profile(
            input_dir,
            ingest_report,
            output_dir,
            options or ProfileOptions(),
            header_map,
        )
    except IngestError:
        raise
    except (OSError, ValueError, KeyError, TypeError, IndexError, duckdb.Error) as exc:
        raise IngestError(
            "profile_artifact", "Profile inputs are invalid or inaccessible"
        ) from exc
