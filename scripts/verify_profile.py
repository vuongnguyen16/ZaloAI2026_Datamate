"""Independent SQL aggregate audit of engineering profiles, local only.

Does not call production profile/statistics code. Gold is binary-hashed only.
"""

import argparse
import hashlib
import json
import re
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path

from datamate.artifacts import sha256, write_json
from datamate.ingest.loader import connect, disjoint, identifier


def snapshot(root):
    return {
        p.relative_to(root).as_posix(): sha256(p)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def expected_preview(text, limit):
    if text is None:
        return {"value": None, "utf8_bytes": None, "truncated": False}
    encoded = text.encode("utf-8")
    result = {
        "value": text,
        "utf8_bytes": len(encoded),
        "truncated": len(encoded) > limit,
    }
    if result["truncated"]:
        prefix = text
        # Independent code-point slicing rather than slicing encoded bytes.
        size = 0
        for i, char in enumerate(text):
            size += len(char.encode("utf-8"))
            if size > limit:
                prefix = text[:i]
                break
        result.update(value=prefix, sha256=hashlib.sha256(encoded).hexdigest())
    return result


def check(condition, bid, name, position, check_name):
    if not condition:
        raise ValueError(
            f"Profile mismatch: business={bid}, unit={name}, column={position}, check={check_name}"
        )


def audit_unit(con, unit, options, bid):
    table = identifier(unit["storage_table"])
    kind = unit["source_kind"]
    typ = (
        "'csv:text'"
        if kind == "csv"
        else ("'xlsx:'" if kind == "xlsx_sheet" else "'sqlite:'")
        + " || substr(json_extract_string(__payload, '$.m.types'),CAST(j.key AS INTEGER),1)"
    )
    flat = f"SELECT __row,CAST(j.key AS INTEGER) AS position,json_extract_string(j.value,'$') AS raw,{typ} AS typ FROM {table},json_each(json_extract(__payload,'$.v')) j"
    row_count, nonempty, width = con.execute(
        f"SELECT count(*),count(*) FILTER(WHERE EXISTS(SELECT 1 FROM json_each(json_extract(__payload,'$.v')) c WHERE json_extract_string(c.value,'$') IS NOT NULL AND json_extract_string(c.value,'$')<>'')),coalesce(max(__width),0) FROM {table}"
    ).fetchone()
    check(
        row_count == unit["row_count"] and nonempty == unit["nonempty_rows"],
        bid,
        unit["source_name"],
        0,
        "row counts",
    )
    check(
        kind == "sqlite_table" or width == unit["max_width"],
        bid,
        unit["source_name"],
        0,
        "max width",
    )
    grouped = con.execute(f"""WITH flat AS ({flat})
        SELECT position,typ,count(*),count(*) FILTER(WHERE raw IS NULL),count(*) FILTER(WHERE raw=''),
        min(nullif(raw,'')),max(nullif(raw,'')),
        min(length(nullif(raw,''))),max(length(nullif(raw,''))),
        min(octet_length(encode(nullif(raw,'')))) ,max(octet_length(encode(nullif(raw,''))))
        FROM flat GROUP BY position,typ""").fetchall()
    actual = {
        i: {
            "present": 0,
            "null": 0,
            "empty": 0,
            "types": {},
            "min": None,
            "max": None,
            "min_chars": None,
            "max_chars": None,
            "min_utf8_bytes": None,
            "max_utf8_bytes": None,
        }
        for i in range(1, unit["max_width"] + 1)
    }
    for (
        i,
        physical,
        count,
        nulls,
        empty,
        low,
        high,
        minchars,
        maxchars,
        minbytes,
        maxbytes,
    ) in grouped:
        d = actual[i]
        d["present"] += count
        d["null"] += nulls
        d["empty"] += empty
        d["types"][physical] = count
        for key, value in [
            ("min", low),
            ("max", high),
            ("min_chars", minchars),
            ("max_chars", maxchars),
            ("min_utf8_bytes", minbytes),
            ("max_utf8_bytes", maxbytes),
        ]:
            if value is not None:
                d[key] = (
                    value
                    if d[key] is None
                    else (
                        min(d[key], value)
                        if key.startswith("min")
                        else max(d[key], value)
                    )
                )
    numeric = {
        i: {
            "finite": 0,
            "nonfinite": 0,
            "invalid": 0,
            "too_long": 0,
            "low": None,
            "high": None,
        }
        for i in actual
    }
    cursor = con.execute(
        f"WITH flat AS ({flat}) SELECT position,raw FROM flat WHERE typ IN ('xlsx:n','sqlite:i','sqlite:r') AND raw IS NOT NULL AND raw<>'' ORDER BY __row,position"
    )
    while batch := cursor.fetchmany(1024):
        for i, text in batch:
            d = numeric[i]
            if len(text) > options["max_numeric_chars"]:
                d["too_long"] += 1
                continue
            try:
                number = Decimal(text)
            except InvalidOperation:
                d["invalid"] += 1
                continue
            if not number.is_finite():
                d["nonfinite"] += 1
            elif not re.fullmatch(
                r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", text
            ):
                d["invalid"] += 1
            else:
                d["finite"] += 1
                if d["low"] is None or number < d["low"][0]:
                    d["low"] = (number, text)
                if d["high"] is None or number > d["high"][0]:
                    d["high"] = (number, text)
    check(
        [c["position"] for c in unit["columns"]] == list(actual),
        bid,
        unit["source_name"],
        0,
        "column coverage",
    )
    coordinates = {
        r["source_row"]
        for r in unit["row_preview"] + unit["header"]["selected_row_evidence"]
    }
    coordinates.update(s["source_row"] for c in unit["columns"] for s in c["samples"])
    coordinates.update(
        s["source_row"] for c in unit["columns"] for s in c.get("data_samples", [])
    )
    evidence = {}
    if coordinates:
        for row, rowwidth, payload in con.execute(
            f"SELECT __row,__width,CAST(__payload AS VARCHAR) FROM {table} WHERE __row IN ({','.join('?' for _ in coordinates)})",
            sorted(coordinates),
        ).fetchall():
            evidence[row] = (rowwidth, json.loads(payload))
    for c in unit["columns"]:
        i = c["position"]
        d, n = actual[i], numeric[i]
        counts = {
            "present": d["present"],
            "missing": row_count - d["present"],
            "null": d["null"],
            "empty": d["empty"],
            "nonempty": d["present"] - d["null"] - d["empty"],
        }
        check(c["counts"] == counts, bid, unit["source_name"], i, "cell counts")
        check(
            c["ratios"]
            == {k: v / row_count if row_count else None for k, v in counts.items()},
            bid,
            unit["source_name"],
            i,
            "ratios",
        )
        check(
            c["physical_types"] == d["types"],
            bid,
            unit["source_name"],
            i,
            "physical types",
        )
        check(
            c["length_nonempty"]
            == {
                k: d[k]
                for k in ["min_chars", "max_chars", "min_utf8_bytes", "max_utf8_bytes"]
            },
            bid,
            unit["source_name"],
            i,
            "length extrema",
        )
        for key in ["min", "max"]:
            check(
                c["lexical_nonempty"][key]
                == (
                    expected_preview(d[key], options["value_bytes"])
                    if d[key] is not None
                    else None
                ),
                bid,
                unit["source_name"],
                i,
                "lexical extrema",
            )
        expected_numeric = {
            k: n[k] for k in ["finite", "nonfinite", "invalid", "too_long"]
        }
        expected_numeric.update(
            min_lexeme=n["low"][1] if n["low"] else None,
            max_lexeme=n["high"][1] if n["high"] else None,
        )
        check(
            {k: c["numeric_physical_nonempty"][k] for k in expected_numeric}
            == expected_numeric,
            bid,
            unit["source_name"],
            i,
            "numeric extrema",
        )
        for s in c["samples"] + c.get("data_samples", []):
            original = evidence[s["source_row"]][1]
            value = original["v"][str(i)]
            check(
                {
                    k: v
                    for k, v in s.items()
                    if k not in {"source_row", "line_start", "line_end"}
                }
                == expected_preview(value, options["value_bytes"]),
                bid,
                unit["source_name"],
                i,
                "sample source value",
            )
            if kind == "csv":
                check(
                    all(s[k] == original["m"][k] for k in ["line_start", "line_end"]),
                    bid,
                    unit["source_name"],
                    i,
                    "CSV sample lines",
                )
        for s in c.get("data_samples", []):
            check(
                unit["header"].get("data_start_row") is not None
                and s["source_row"] >= unit["header"]["data_start_row"],
                bid,
                unit["source_name"],
                i,
                "data sample boundary",
            )
        for label in c["header_cells"]:
            original = evidence[label["source_row"]][1]["v"]
            cell = label["cell"]
            check(
                (cell is None and str(i) not in original)
                or (
                    cell is not None
                    and {k: v for k, v in cell.items() if k != "physical_type"}
                    == expected_preview(original[str(i)], options["value_bytes"])
                ),
                bid,
                unit["source_name"],
                i,
                "header cell provenance",
            )
    return {
        "source_name": unit["source_name"],
        "source_file": unit["source_file"],
        "columns": len(actual),
        "rows": row_count,
        "match": True,
    }


def verify(input_dir, profile_report, output_dir):
    source, report_path, output = (
        input_dir.resolve(strict=True),
        profile_report.resolve(strict=True),
        output_dir.resolve(),
    )
    if not disjoint(source, report_path):
        raise ValueError("Profile report must be outside raw")
    report = json.loads(report_path.read_text("utf-8"))
    ingest = json.loads(Path(report["ingest_report"]).read_text("utf-8"))
    cache = Path(ingest["cache_root"]).resolve()
    if output.exists() or any(
        not disjoint(output, p) for p in (source, cache, report_path.parent)
    ):
        raise ValueError("Audit output must be new and disjoint from inputs")
    if not report["valid"]:
        raise ValueError("Cannot certify a failed profile report")
    before = snapshot(source)
    cache_before = snapshot(cache)
    records = []
    start = time.perf_counter()
    for b in report["businesses"]:
        profile_path, schema_path = (
            Path(b["profile"]["path"]),
            Path(b["schema"]["path"]),
        )
        if (
            sha256(profile_path) != b["profile"]["sha256"]
            or sha256(schema_path) != b["schema"]["sha256"]
        ):
            raise ValueError("Profile/schema hash mismatch")
        profile = json.loads(profile_path.read_text("utf-8"))
        schema = json.loads(schema_path.read_text("utf-8"))
        prov = profile["provenance"]
        if sha256(Path(prov["database"])) != prov["database_sha256"]:
            raise ValueError("Raw cache hash mismatch")
        manifest = next(
            x for x in ingest["businesses"] if x["business_id"] == b["business_id"]
        )
        check(
            [
                (u["source_file"], u["source_name"], u["source_kind"])
                for u in profile["units"]
            ]
            == [
                (u["source_file"], u["source_name"], u["source_kind"])
                for u in manifest["units"]
            ],
            b["business_id"],
            "all",
            0,
            "unit coverage",
        )
        check(
            [t["sql_name"] for t in schema["tables"]]
            == [u["view_name"] for u in profile["units"]],
            b["business_id"],
            "all",
            0,
            "schema tables",
        )
        with connect(Path(prov["database"]), read_only=True) as con:
            for unit, descriptor in zip(
                profile["units"], schema["tables"], strict=True
            ):
                actual = con.execute(
                    f"DESCRIBE {identifier(unit['view_name'])}"
                ).fetchall()[3:]
                check(
                    [(c["sql_name"], c["sql_type"]) for c in descriptor["columns"]]
                    == [(r[0], r[1]) for r in actual],
                    b["business_id"],
                    unit["source_name"],
                    0,
                    "query schema",
                )
                if "structure" in unit:
                    check(
                        descriptor["header_status"] == unit["header"]["status"]
                        and descriptor["header_rows"] == unit["header"]["rows"]
                        and descriptor["data_start_row"]
                        == unit["header"]["data_start_row"],
                        b["business_id"],
                        unit["source_name"],
                        0,
                        "structure descriptor",
                    )
                    check(
                        descriptor["text_quality"] == unit["text_quality"],
                        b["business_id"],
                        unit["source_name"],
                        0,
                        "text evidence descriptor",
                    )
                records.append(
                    {
                        "business_id": b["business_id"],
                        **audit_unit(con, unit, profile["options"], b["business_id"]),
                    }
                )
        print("Verified profile", b["business_id"], flush=True)
    after, cache_after = snapshot(source), snapshot(cache)
    result = {
        "valid": before == after and cache_before == cache_after,
        "scope": "independent SQL full aggregates/types/extrema and sample-coordinate audit; no model/PA",
        "businesses": len(report["businesses"]),
        "units": len(records),
        "columns": sum(r["columns"] for r in records),
        "rows": sum(r["rows"] for r in records),
        "raw_unchanged": before == after,
        "cache_unchanged": cache_before == cache_after,
        "raw_sha256_before": before,
        "raw_sha256_after": after,
        "cache_sha256_before": cache_before,
        "cache_sha256_after": cache_after,
        "records": records,
        "gold_content_parsed": False,
        "duration_seconds": time.perf_counter() - start,
    }
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "verification.json", result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = verify(a.input, a.report, a.output)
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "valid",
                    "businesses",
                    "units",
                    "columns",
                    "rows",
                    "raw_unchanged",
                    "cache_unchanged",
                    "duration_seconds",
                ]
            }
        )
    )
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
