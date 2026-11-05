"""Lossless synthetic round trips, cache lifecycle and failure isolation."""

import csv
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from datamate.ingest import (
    IngestError,
    LoaderOptions,
    ingest_business,
    loader,
)
from datamate.ingest.loader import run_ingest
from scripts.verify_ingest import verify


def make_xlsx(path, *, strict=False, external=False, dtd=False):
    ns = (
        "http://purl.oclc.org/ooxml/spreadsheetml/main"
        if strict
        else "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    )
    rel = (
        "http://purl.oclc.org/ooxml/officeDocument/relationships"
        if strict
        else "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    )
    with ZipFile(path, "w", ZIP_DEFLATED) as z:
        z.writestr(
            "xl/workbook.xml",
            f'''<workbook xmlns="{ns}" xmlns:r="{rel}"><workbookPr date1904="1"/><sheets><sheet name="Bảng 'raw'" sheetId="1" r:id="r1"/><sheet name="Hidden" state="hidden" sheetId="2" r:id="r2"/></sheets></workbook>''',
        )
        mode = 'TargetMode="External"' if external else ""
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            f'''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Type="{rel}/worksheet" Target="worksheets/sheet1.xml" {mode}/><Relationship Id="r2" Type="{rel}/worksheet" Target="/xl/worksheets/sheet2.xml"/></Relationships>''',
        )
        z.writestr(
            "xl/styles.xml",
            f'''<styleSheet xmlns="{ns}"><numFmts count="1"><numFmt numFmtId="164" formatCode="dd/mm/yyyy"/></numFmts><cellXfs count="2"><xf numFmtId="0"/><xf numFmtId="164"/></cellXfs></styleSheet>''',
        )
        z.writestr(
            "xl/sharedStrings.xml",
            f'''<sst xmlns="{ns}"><si><t>0012</t></si><si><r><t>Cà</t></r><r><t xml:space="preserve"> phê</t></r><rPh sb="0" eb="1"><t>phonetic annotation</t></rPh></si></sst>''',
        )
        prefix = (
            '<!DOCTYPE worksheet [<!ENTITY secret "do not expand">]>' if dtd else ""
        )
        z.writestr(
            "xl/worksheets/sheet1.xml",
            prefix
            + f'''<worksheet xmlns="{ns}"><dimension ref="A1:Z100"/><sheetData>
<row r="1"><c r="A1" t="inlineStr"><is><t>Header group</t></is></c><c r="C1" t="inlineStr"><is><t>Header group</t></is></c></row>
<row r="2"><c r="A2" t="inlineStr"><is><t>Code</t></is></c></row><row r="3"/>
<row r="4" hidden="1"><c r="A4" t="s"><v>0</v></c><c r="B4" t="n" s="1"><v>45689</v></c><c r="D4" t="n"><f>SUM(B4,1)</f><v>45690</v></c><c r="E4"><f>1+1</f></c><c r="F4" t="inlineStr"><is><t/></is></c><c r="G4" t="b"><v>0</v></c><c r="H4" t="e"><v>#N/A</v></c></row>
<row r="8"><c r="A8" t="s"><v>1</v></c></row></sheetData><mergeCells><mergeCell ref="A1:C1"/></mergeCells></worksheet>''',
        )
        z.writestr(
            "xl/worksheets/sheet2.xml",
            f'''<worksheet xmlns="{ns}"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>hidden data</t></is></c></row></sheetData></worksheet>''',
        )


@pytest.fixture
def inputs(tmp_path):
    root = tmp_path / "input"
    biz = root / "data" / "tenant_alpha"
    biz.mkdir(parents=True)
    (biz / "README.md").write_text(
        "Synthetic README. DELETE is only data.", encoding="utf-8"
    )
    (root / "answers.jsonl").write_text("GOLD MUST NEVER BE OPENED", encoding="utf-8")
    rows = [
        ["code", "label", "label"],
        ["0012", "  raw  ", ""],
        [],
        ["NULL"],
        ['quote"value', "a\r\nb", "a\0b", "25k"],
        ["1tr090", "Cà phê", ""],
    ]
    with (biz / "sales.csv").open("w", encoding="utf-8-sig", newline="") as h:
        csv.writer(h, lineterminator="\r\n").writerows(rows)
    make_xlsx(biz / "book's.xlsx")
    with closing(sqlite3.connect(biz / "pos.sqlite")) as con:
        con.execute('CREATE TABLE "odd""table" (code TEXT, value, blank TEXT, blob)')
        con.executemany(
            'INSERT INTO "odd""table" VALUES (?,?,?,?)',
            [("0012", 2**63 - 1, "", b"\0\xff"), ("NULL", 0.1, None, b"")],
        )
        con.execute("CREATE TABLE empty_table(x TEXT,y INTEGER)")
        con.commit()
    return root, biz, rows


def values(result, unit, *fields):
    item = next(u for u in result["units"] if u["source_name"] == unit)
    with loader.connect(Path(result["database"]), read_only=True) as con:
        return con.execute(
            f"SELECT {','.join(fields)} FROM {loader.identifier(item['view_name'])} ORDER BY __row"
        ).fetchall()


def test_all_formats_preserve_values_coordinates_metadata_and_raw(
    inputs, tmp_path, monkeypatch
):
    root, biz, rows = inputs
    before = {p.name: p.read_bytes() for p in biz.iterdir()}
    original_open = Path.open

    def guard(path, *args, **kwargs):
        assert path.name != "answers.jsonl", "gold was opened"
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guard)
    result = ingest_business(root, biz.name, tmp_path / "cache")
    assert not result["cache_hit"] and len(result["units"]) == 5
    expected_csv = [
        (i, len(row), *(row + [None] * (4 - len(row)))) for i, row in enumerate(rows, 1)
    ]
    assert (
        values(result, "sales", "__row", "__width", "c0001", "c0002", "c0003", "c0004")
        == expected_csv
    )
    assert values(
        result,
        "Bảng 'raw'",
        "__row",
        "__width",
        "c0001",
        "c0002",
        "c0004",
        "c0005",
        "c0006",
        "c0007",
        "c0008",
    ) == [
        (1, 3, "Header group", None, None, None, None, None, None),
        (2, 1, "Code", None, None, None, None, None, None),
        (3, 0, None, None, None, None, None, None, None),
        (4, 8, "0012", "45689", "45690", None, "", "0", "#N/A"),
        (8, 1, "Cà phê", None, None, None, None, None, None),
    ]
    meta = json.loads(values(result, "Bảng 'raw'", "__metadata")[3][0])
    assert meta["styles"] == {"2": "1"}
    assert meta["formulas"]["4"]["text"] == "SUM(B4,1)"
    assert meta["formulas"]["5"]["text"] == "1+1"
    assert meta["row_attributes"]["hidden"] == "1"
    assert values(result, "Hidden", "c0001") == [("hidden data",)]
    assert values(result, 'odd"table', "c0001", "c0002", "c0003", "c0004") == [
        ("0012", str(2**63 - 1), "", "AP8="),
        ("NULL", "0.1", None, ""),
    ]
    assert (
        json.loads(values(result, 'odd"table', "__metadata")[0][0])["types"] == "titb"
    )
    assert values(result, "empty_table", "c0001", "c0002") == []
    manifest = json.loads(Path(result["manifest"]).read_text("utf-8"))
    assert (
        manifest["source_metadata"]["book's.xlsx"]["workbook_properties"]["date1904"]
        == "1"
    )
    assert manifest["units"][1]["frame_sha256"]
    assert {p.name: p.read_bytes() for p in biz.iterdir()} == before


def test_cache_hit_without_reparse_and_invalidation(inputs, tmp_path, monkeypatch):
    root, biz, _ = inputs
    cache = tmp_path / "cache"
    first = ingest_business(root, biz.name, cache)
    stamp = Path(first["database"]).stat().st_mtime_ns
    with monkeypatch.context() as m:
        m.setattr(
            loader,
            "read_source",
            lambda *a: (_ for _ in ()).throw(AssertionError("reparsed")),
        )
        second = ingest_business(root, biz.name, cache)
    assert second["cache_hit"] and second["fingerprint"] == first["fingerprint"]
    assert Path(first["database"]).stat().st_mtime_ns == stamp
    (biz / "README.md").write_text("Changed metadata", encoding="utf-8")
    third = ingest_business(root, biz.name, cache)
    assert not third["cache_hit"] and third["fingerprint"] != first["fingerprint"]
    (biz / "sales.csv").write_text("id\n0099\n", encoding="utf-8")
    fourth = ingest_business(root, biz.name, cache)
    assert fourth["fingerprint"] != third["fingerprint"]
    fifth = ingest_business(
        root, biz.name, cache, replace(LoaderOptions(), max_rows=100)
    )
    assert fifth["fingerprint"] != fourth["fingerprint"]
    monkeypatch.setattr(loader, "code_hash", lambda: "f" * 64)
    sixth = ingest_business(root, biz.name, cache)
    assert sixth["fingerprint"] != fourth["fingerprint"]
    assert Path(first["database"]).exists()


@pytest.mark.parametrize("corruption", ["database", "catalog"])
def test_corrupt_cache_not_reused_or_overwritten(inputs, tmp_path, corruption):
    root, biz, _ = inputs
    cache = tmp_path / "cache"
    first = ingest_business(root, biz.name, cache)
    if corruption == "database":
        with Path(first["database"]).open("ab") as h:
            h.write(b"corrupt")
    else:
        p = Path(first["manifest"])
        m = json.loads(p.read_text("utf-8"))
        m["units"][0]["row_count"] += 1
        p.write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(IngestError, match="integrity") as exc:
        ingest_business(root, biz.name, cache)
    assert exc.value.code == "cache_corrupt"


def test_input_change_during_build_leaves_no_complete_cache(
    inputs, tmp_path, monkeypatch
):
    root, biz, _ = inputs
    original = loader.read_source

    def mutating(path, options):
        yield from original(path, options)
        if path.suffix == ".csv":
            path.write_text("changed\n", encoding="utf-8")

    monkeypatch.setattr(loader, "read_source", mutating)
    with pytest.raises(IngestError) as exc:
        ingest_business(root, biz.name, tmp_path / "cache")
    assert exc.value.code == "input_changed"
    assert not list((tmp_path / "cache").rglob("manifest.json"))
    assert not list((tmp_path / "cache").rglob(".build.lock"))
    assert not list((tmp_path / "cache").rglob(".building-*"))


def test_failed_business_isolated_and_error_contains_location_not_values(
    inputs, tmp_path
):
    root, _, _ = inputs
    bad = root / "data" / "tenant_bad"
    bad.mkdir()
    (bad / "README.md").write_text("Synthetic", encoding="utf-8")
    (bad / "bad.csv").write_bytes(b"col\nPRIVATE_VALUE\xff\n")
    r = run_ingest(root, tmp_path / "cache", tmp_path / "report")
    assert not r["valid"] and r["summary"]["successful"] == 1
    failed = next(b for b in r["businesses"] if not b["valid"])
    assert failed["errors"][0]["code"] == "csv_encoding"
    assert failed["errors"][0]["source_file"] == "bad.csv"
    assert "PRIVATE_VALUE" not in json.dumps(r)
    assert (tmp_path / "report/ingest.json").exists()
    assert len(list((tmp_path / "cache").rglob("manifest.json"))) == 1


@pytest.mark.parametrize(
    "limit,expected",
    [
        ("max_rows", "row_limit"),
        ("max_columns", "column_limit"),
        ("max_cell_bytes", "cell_limit"),
        ("max_staging_bytes", "staging_limit"),
        ("max_units", "unit_limit"),
    ],
)
def test_limits_fail_atomically(inputs, tmp_path, limit, expected):
    root, biz, _ = inputs
    with pytest.raises(IngestError) as exc:
        ingest_business(
            root, biz.name, tmp_path / "cache", replace(LoaderOptions(), **{limit: 1})
        )
    assert exc.value.code == expected
    assert not list((tmp_path / "cache").rglob("manifest.json"))


@pytest.mark.parametrize(
    "failure",
    [
        "view",
        "generated",
        "wal",
        "unknown",
        "csv_quotes",
        "xml_dtd",
        "external",
        "zip_duplicate",
        "xml_truncated",
        "missing_row_coordinate",
    ],
)
def test_unsafe_or_unsupported_sources_do_not_publish(inputs, tmp_path, failure):
    root, biz, _ = inputs
    if failure in {"view", "generated"}:
        with closing(sqlite3.connect(biz / "pos.sqlite")) as con:
            con.execute(
                "CREATE VIEW v AS SELECT secret_function(code) FROM empty_table"
                if failure == "view"
                else "CREATE TABLE generated(x INTEGER,y INTEGER GENERATED ALWAYS AS (x+1))"
            )
            con.commit()
    elif failure == "wal":
        (biz / "pos.sqlite-wal").write_bytes(b"pending")
    elif failure == "unknown":
        (biz / "unhandled.txt").write_text("text")
    elif failure == "csv_quotes":
        (biz / "sales.csv").write_text('"unterminated\n', encoding="utf-8")
    elif failure in {"xml_dtd", "external"}:
        make_xlsx(
            biz / "book's.xlsx",
            external=failure == "external",
            dtd=failure == "xml_dtd",
        )
    elif failure == "zip_duplicate":
        with ZipFile(biz / "book's.xlsx", "a") as z:
            with pytest.warns(UserWarning):
                z.writestr("xl/workbook.xml", "duplicate")
    else:
        path = biz / "book's.xlsx"
        with ZipFile(path) as z:
            members = {n: z.read(n) for n in z.namelist()}
        members["xl/worksheets/sheet1.xml"] = (
            b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1">'
            if failure == "xml_truncated"
            else b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row><c r="A1"/></row></sheetData></worksheet>'
        )
        with ZipFile(path, "w", ZIP_DEFLATED) as z:
            for n, v in members.items():
                z.writestr(n, v)
    with pytest.raises(IngestError):
        ingest_business(root, biz.name, tmp_path / "cache")
    assert not list((tmp_path / "cache").rglob("manifest.json"))


def test_strict_ooxml_and_explicit_csv_encoding(inputs, tmp_path):
    root, biz, _ = inputs
    make_xlsx(biz / "book's.xlsx", strict=True)
    r = ingest_business(root, biz.name, tmp_path / "cache")
    assert values(r, "Bảng 'raw'", "c0001")[-1] == ("Cà phê",)
    for p in biz.iterdir():
        if p.name != "README.md":
            p.unlink()
    (biz / "latin.csv").write_bytes(b"code;label\n0012;caf\xe9\n")
    r = ingest_business(
        root,
        biz.name,
        tmp_path / "cache",
        LoaderOptions(csv_encoding="latin-1", csv_delimiter=";"),
    )
    assert values(r, "latin", "c0001", "c0002") == [("code", "label"), ("0012", "café")]


def test_empty_csv_remains_empty_and_ids_cannot_escape(inputs, tmp_path):
    root, biz, _ = inputs
    for p in biz.iterdir():
        if p.name != "README.md":
            p.unlink()
    (biz / "empty.csv").write_bytes(b"")
    r = ingest_business(root, biz.name, tmp_path / "cache")
    assert r["rows"] == 0 and r["units"][0]["max_width"] == 0
    for bid in ["..", "../tenant_alpha", "a/b", "a:b", " "]:
        with pytest.raises(IngestError):
            ingest_business(root, bid, tmp_path / "cache")


def test_cache_busy_and_output_overlap(inputs, tmp_path):
    root, biz, _ = inputs
    for path in [root, biz / "cache", root.parent]:
        with pytest.raises(IngestError):
            ingest_business(root, biz.name, path)
    cache = tmp_path / "cache"
    ns = cache / ("b_" + hashlib.sha256(biz.name.encode()).hexdigest()[:24])
    ns.mkdir(parents=True)
    (ns / ".build.lock").write_text("busy")
    with pytest.raises(IngestError) as exc:
        ingest_business(root, biz.name, cache)
    assert exc.value.code == "cache_busy"
    for output in [root / "out", cache / "report", tmp_path]:
        with pytest.raises(IngestError):
            run_ingest(root, cache, output)


def test_directory_alias_cannot_bypass_input_protection(inputs, tmp_path):
    root, biz, _ = inputs
    alias = tmp_path / "alias"
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(alias), str(root)], capture_output=True
        )
        if result.returncode:
            pytest.skip("Directory junction unavailable")
    else:
        alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(IngestError) as exc:
        ingest_business(root, biz.name, alias / "cache")
    assert exc.value.code == "output_overlap"
    assert not (root / "cache").exists()


def test_cli_emits_report_and_nonzero_for_bad_input(inputs, tmp_path):
    root, _, _ = inputs
    cmd = [
        sys.executable,
        "-m",
        "datamate.cli",
        "ingest",
        "--input",
        str(root),
        "--cache",
        str(tmp_path / "cache"),
        "--output",
        str(tmp_path / "report"),
    ]
    # Entry point invocation avoids relying on a __main__ block in cli.py.
    cmd = [
        sys.executable,
        "-c",
        "from datamate.cli import main; raise SystemExit(main())",
        *cmd[3:],
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["summary"]["successful"] == 1
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert (
        result.returncode == 2
        and json.loads(result.stdout)["errors"][0]["code"] == "output_overlap"
    )


def test_independent_auditor_checks_all_values_and_detects_tampering(inputs, tmp_path):
    root, _, _ = inputs
    result = run_ingest(root, tmp_path / "cache", tmp_path / "report")
    audit = verify(root, tmp_path / "report/ingest.json", tmp_path / "audit")
    assert audit["valid"] and audit["units"] == 5
    assert audit["rows"] == 14 and audit["nonempty_rows"] == 12
    assert audit["raw_unchanged"]
    business = result["businesses"][0]
    unit = next(u for u in business["units"] if u["source_kind"] == "csv")
    with loader.connect(Path(business["database"])) as con:
        con.execute(
            f"UPDATE {loader.identifier(unit['storage_table'])} SET __payload = ? WHERE __row=1",
            [json.dumps({"v": {"1": "tampered"}, "m": {}})],
        )
    with pytest.raises(ValueError, match="mismatch"):
        verify(root, tmp_path / "report/ingest.json", tmp_path / "audit-bad")
    assert not (tmp_path / "audit-bad").exists()


def test_large_csv_field_is_preserved_and_independently_audited(inputs, tmp_path):
    root, biz, _ = inputs
    content = "a" * 150_000
    (biz / "large.csv").write_text(content + "\n", encoding="utf-8")
    previous_limit = csv.field_size_limit()
    csv.field_size_limit(17)
    try:
        result = run_ingest(root, tmp_path / "cache", tmp_path / "report")
        assert csv.field_size_limit() == 17
        assert values(result["businesses"][0], "large", "c0001") == [(content,)]
        audit = verify(root, tmp_path / "report/ingest.json", tmp_path / "audit")
        assert audit["valid"] and audit["units"] == 6
        assert csv.field_size_limit() == 17
    finally:
        csv.field_size_limit(previous_limit)
