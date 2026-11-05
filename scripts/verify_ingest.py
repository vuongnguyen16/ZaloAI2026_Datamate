"""Independent source-value audit of a raw ingest report, without parsing gold.

No production readers are used. Root files (including gold) are binary-hashed
only to verify non-mutation. Source values remain local and are never reported.
"""

import argparse
import base64
import csv
import hashlib
import itertools
import json
import posixpath
import re
import sqlite3
import time
import xml.etree.ElementTree as ET
from contextlib import closing
from pathlib import Path
from zipfile import ZipFile

from datamate.artifacts import sha256, write_json
from datamate.ingest.loader import connect, disjoint, identifier


def snapshot_tree(root):
    return {
        p.relative_to(root).as_posix(): sha256(p)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def string_content(element):
    if element is None:
        return ""
    result = []
    for child in element:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "t":
            result.append(child.text or "")
        elif tag == "r":
            result.extend(
                t.text or "" for t in child if t.tag.rsplit("}", 1)[-1] == "t"
            )
    return "".join(result)


def independent_xlsx(path):
    with ZipFile(path) as z:
        book = ET.fromstring(z.read("xl/workbook.xml"))
        ns = book.tag.split("}")[0] + "}"
        rels = {
            e.attrib["Id"]: e.attrib["Target"]
            for e in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        }
        strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = None
            for event, node in ET.iterparse(
                z.open("xl/sharedStrings.xml"), events=("start", "end")
            ):
                if root is None:
                    root = node
                if event == "end" and node.tag == ns + "si":
                    strings.append(string_content(node))
                    node.clear()
                    root.remove(node)
        for sh in book.find(ns + "sheets"):
            rid = next(v for k, v in sh.attrib.items() if k.endswith("}id"))
            target = rels[rid]
            member = posixpath.normpath(
                target.lstrip("/") if target.startswith("/") else "xl/" + target
            )
            if not member.startswith("xl/"):
                raise ValueError("Invalid worksheet relationship")

            def rows(member=member):
                parent = None
                with z.open(member) as h:
                    for event, node in ET.iterparse(h, events=("start", "end")):
                        if event == "start" and node.tag == ns + "sheetData":
                            parent = node
                        if event != "end" or node.tag != ns + "row":
                            continue
                        cells = {}
                        physical = {}
                        for cell in node:
                            if cell.tag != ns + "c":
                                continue
                            letters = re.match(r"[A-Z]+", cell.attrib["r"])[0]
                            index = 0
                            for letter in letters:
                                index = index * 26 + ord(letter) - ord("A") + 1
                            typ = cell.attrib.get("t", "n")
                            physical[str(index)] = typ
                            item = cell.find(ns + "v")
                            value = item.text if item is not None else None
                            if typ == "s":
                                value = strings[int(value)]
                            elif typ == "inlineStr":
                                value = string_content(cell.find(ns + "is"))
                            cells[str(index)] = value
                        yield (
                            int(node.attrib["r"]),
                            max(map(int, cells), default=0),
                            cells,
                            physical,
                        )
                        node.clear()
                        parent.remove(node)

            yield sh.attrib["name"], "xlsx_sheet", rows()


def independent_sources(path, options):
    if path.suffix.lower() == ".xlsx":
        yield from independent_xlsx(path)
    elif path.suffix.lower() == ".csv":

        def rows():
            previous_limit = csv.field_size_limit()
            csv.field_size_limit(options["max_cell_bytes"])
            try:
                with path.open(encoding=options["csv_encoding"], newline="") as h:
                    for number, row in enumerate(
                        csv.reader(h, delimiter=options["csv_delimiter"], strict=True),
                        1,
                    ):
                        yield (
                            number,
                            len(row),
                            {str(i): value for i, value in enumerate(row, 1)},
                            None,
                        )
            finally:
                csv.field_size_limit(previous_limit)

        yield path.stem, "csv", rows()
    else:
        with closing(
            sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
        ) as con:
            con.execute("PRAGMA query_only=ON")
            con.execute("PRAGMA trusted_schema=OFF")
            for name, kind in con.execute(
                "SELECT name,type FROM sqlite_master WHERE type IN ('view','table') ORDER BY name"
            ).fetchall():
                if name.startswith("sqlite_"):
                    continue
                if kind != "table":
                    raise ValueError("Unexpected SQLite view in audited source")

                def rows(name=name):
                    for number, row in enumerate(
                        con.execute("SELECT * FROM " + identifier(name)), 1
                    ):
                        cells, physical = {}, {}
                        for i, value in enumerate(row, 1):
                            physical[str(i)] = type(value).__name__
                            cells[str(i)] = (
                                base64.b64encode(value).decode("ascii")
                                if isinstance(value, bytes)
                                else None
                                if value is None
                                else repr(value)
                                if isinstance(value, float)
                                else str(value)
                            )
                        yield number, len(row), cells, physical

                yield name, "sqlite_table", rows()


def stored_rows(con, table):
    cursor = con.execute(
        f"SELECT __row,__width,CAST(__payload AS VARCHAR) FROM {identifier(table)} ORDER BY __row"
    )
    while rows := cursor.fetchmany(1024):
        for number, width, payload in rows:
            parsed = json.loads(payload)
            yield number, width, parsed["v"], parsed["m"]


def verify(input_dir: Path, ingest_report: Path, output_dir: Path) -> dict:
    source = input_dir.resolve(strict=True)
    output = output_dir.resolve()
    report = json.loads(ingest_report.read_text("utf-8"))
    cache = Path(report["cache_root"]).resolve()
    if output.exists() or not disjoint(source, output) or not disjoint(cache, output):
        raise ValueError("Audit output must be new and outside input/cache")
    if not report["valid"]:
        raise ValueError("Cannot certify a failed ingest report")
    before = snapshot_tree(source)
    records = []
    started = time.perf_counter()
    for business in report["businesses"]:
        bid = business["business_id"]
        if bid in {".", ".."} or any(c in bid for c in "/\\:"):
            raise ValueError("Invalid business identity in report")
        root = source / "data" / bid
        manifest = json.loads(Path(business["manifest"]).read_text("utf-8"))
        units = {
            (u["source_file"], u["source_name"], u["source_kind"]): u
            for u in business["units"]
        }
        if len(units) != len(business["units"]):
            raise ValueError("Duplicate unit in ingest report")
        seen = set()
        with connect(Path(business["database"]), read_only=True) as con:
            readme_codec = (
                manifest["source_metadata"]
                .get("README.md", {})
                .get("encoding", "utf-8-sig")
            )
            if con.execute("SELECT text FROM __dm_readme").fetchone()[0] != (
                root / "README.md"
            ).read_text(encoding=readme_codec):
                raise ValueError("Cached README differs from strictly decoded source")
            files = sorted(
                p
                for p in root.rglob("*")
                if p.is_file() and p.suffix.lower() in {".csv", ".xlsx", ".sqlite"}
            )
            for path in files:
                rel = path.relative_to(root).as_posix()
                expected_hash = next(
                    f["sha256"]
                    for f in manifest["signature"]["files"]
                    if f["path"] == rel
                )
                if sha256(path) != expected_hash:
                    raise ValueError("Source hash differs from ingestion manifest")
                for name, kind, rows in independent_sources(
                    path,
                    {
                        **manifest["signature"]["options"],
                        "csv_encoding": manifest["source_metadata"]
                        .get(rel, {})
                        .get(
                            "encoding", manifest["signature"]["options"]["csv_encoding"]
                        ),
                        "csv_delimiter": manifest["source_metadata"]
                        .get(rel, {})
                        .get(
                            "delimiter",
                            manifest["signature"]["options"]["csv_delimiter"],
                        ),
                    },
                ):
                    key = (rel, name, kind)
                    unit = units[key]
                    if not re.fullmatch(r"rows_[0-9a-f]{24}", unit["storage_table"]):
                        raise ValueError("Unexpected cached table identity")
                    seen.add(key)
                    digest, count, nonempty = hashlib.sha256(), 0, 0
                    sentinel = object()
                    for expected, actual in itertools.zip_longest(
                        rows,
                        stored_rows(con, unit["storage_table"]),
                        fillvalue=sentinel,
                    ):
                        if (
                            expected is sentinel
                            or actual is sentinel
                            or expected[:3] != actual[:3]
                        ):
                            raise ValueError(
                                f"Raw value/position mismatch: {bid}/{rel}/{name}, row ordinal {count + 1}"
                            )
                        physical = expected[3]
                        if physical is not None:
                            codes = (
                                {
                                    "n": "n",
                                    "inlineStr": "i",
                                    "s": "s",
                                    "str": "x",
                                    "b": "b",
                                    "e": "e",
                                    "d": "d",
                                }
                                if kind == "xlsx_sheet"
                                else {
                                    "NoneType": "0",
                                    "str": "t",
                                    "bytes": "b",
                                    "int": "i",
                                    "float": "r",
                                }
                            )
                            for i, typ in physical.items():
                                if actual[3]["types"][int(i) - 1] != codes[typ]:
                                    raise ValueError(
                                        "Physical cell type differs from source"
                                    )
                        digest.update(
                            json.dumps(
                                expected[:3],
                                ensure_ascii=False,
                                sort_keys=True,
                                separators=(",", ":"),
                            ).encode("utf-8")
                            + b"\n"
                        )
                        count += 1
                        nonempty += any(
                            v is not None and v != "" for v in expected[2].values()
                        )
                    if count != unit["row_count"] or nonempty != unit["nonempty_rows"]:
                        raise ValueError(
                            "Unit row counts differ from independent parser"
                        )
                    records.append(
                        {
                            "business_id": bid,
                            "source_file": rel,
                            "source_name": name,
                            "kind": kind,
                            "rows": count,
                            "nonempty_rows": nonempty,
                            "independent_value_sha256": digest.hexdigest(),
                            "match": True,
                        }
                    )
        if seen != set(units):
            raise ValueError("Source unit coverage differs from ingestion report")
        print(
            f"Verified {bid}: {sum(r['rows'] for r in records if r['business_id'] == bid)} rows",
            flush=True,
        )
    after = snapshot_tree(source)
    result = {
        "valid": before == after,
        "scope": "independent full source-value/type/position audit, not model/PA",
        "businesses": len(report["businesses"]),
        "units": len(records),
        "rows": sum(r["rows"] for r in records),
        "nonempty_rows": sum(r["nonempty_rows"] for r in records),
        "raw_unchanged": before == after,
        "raw_sha256_before": before,
        "raw_sha256_after": after,
        "records": records,
        "duration_seconds": time.perf_counter() - started,
        "gold_content_parsed": False,
    }
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "verification.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.input, args.report, args.output)
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "valid",
                    "businesses",
                    "units",
                    "rows",
                    "nonempty_rows",
                    "raw_unchanged",
                    "duration_seconds",
                ]
            }
        )
    )
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
