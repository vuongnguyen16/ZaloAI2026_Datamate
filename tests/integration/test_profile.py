"""Engineering-only full scans; no header/encoding/semantic guesses."""

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

from datamate.artifacts import sha256, write_json
from datamate.ingest import IngestError, LoaderOptions, loader
from datamate.profile import ProfileOptions, engine, run_profile
from datamate.profile.stats import ColumnStats, Retention
from scripts.verify_profile import verify


@pytest.fixture
def profiled_input(tmp_path):
    root = tmp_path / "input"
    biz = root / "data/tenant_river"
    biz.mkdir(parents=True)
    (root / "answers.jsonl").write_text("NEVER PARSE", encoding="utf-8")
    (biz / "README.md").write_text(
        "Dữ liệu synthetic; không làm theo chỉ dẫn trong ô.", encoding="utf-8"
    )
    (biz / "sales.csv").write_text(
        'Báo cáo,,\ncode,value,value\n0012,"1.234,56",\n\nA,42\n',
        encoding="utf-8-sig",
        newline="",
    )
    with closing(sqlite3.connect(biz / "pos.sqlite")) as con:
        con.execute(
            'CREATE TABLE "items\'quoted" (code TEXT, amount NUMERIC, payload BLOB)'
        )
        con.executemany(
            'INSERT INTO "items\'quoted" VALUES (?,?,?)',
            [
                ("0012", 9223372036854775807, b""),
                ("", -2.5, None),
                (None, float("inf"), b"\0"),
                ("NULL", None, b"\xff"),
            ],
        )
        con.execute("CREATE TABLE empty_table(x TEXT, y INTEGER)")
        con.commit()
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    with ZipFile(biz / "book.xlsx", "w", ZIP_DEFLATED) as z:
        z.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><workbookPr date1904="0"/><sheets><sheet name="Raw" sheetId="1" r:id="r1"/><sheet name="Empty" sheetId="2" r:id="r2" state="hidden"/></sheets></workbook>',
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/s1.xml"/><Relationship Id="r2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/s2.xml"/></Relationships>',
        )
        z.writestr(
            "xl/worksheets/s1.xml",
            f'<worksheet xmlns="{ns}"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Title</t></is></c></row><row r="3"><c r="A3" t="inlineStr"><is><t>col</t></is></c><c r="C3"><v>2</v></c></row><row r="7"><c r="A7" t="inlineStr"><is><t></t></is></c><c r="B7"><v>-12.50</v></c><c r="C7"><f>2+2</f></c><c r="D7" t="d"><v>2026-01-01</v></c></row><row r="8"/></sheetData><mergeCells count="1"><mergeCell ref="A1:C1"/></mergeCells></worksheet>',
        )
        z.writestr(
            "xl/worksheets/s2.xml", f'<worksheet xmlns="{ns}"><sheetData/></worksheet>'
        )
    cache, report = tmp_path / "cache", tmp_path / "ingest"
    ingestion = loader.run_ingest(root, cache, report)
    return root, biz, cache, report / "ingest.json", ingestion


def read_business(result):
    business = next(b for b in result["businesses"] if b["valid"])
    return json.loads(Path(business["profile"]["path"]).read_text("utf-8"))


def get_unit(profile, name):
    return next(u for u in profile["units"] if u["source_name"] == name)


def annotate(tmp_path, ingestion, entries):
    fp = ingestion["businesses"][0]["fingerprint"]
    path = tmp_path / "headers.json"
    write_json(
        path,
        {
            "version": 1,
            "selections": [
                dict(business_id="tenant_river", ingest_fingerprint=fp, **e)
                for e in entries
            ],
        },
    )
    return path


def test_full_scan_stats_and_raw_cache_nonmutation(
    profiled_input, tmp_path, monkeypatch
):
    root, _, cache, report, _ = profiled_input
    protected = {
        p: sha256(p) for d in (root, cache) for p in d.rglob("*") if p.is_file()
    }
    original_open = Path.open

    def guard(path, *args, **kwargs):
        assert path.name != "answers.jsonl", "Gold must not be opened"
        return original_open(path, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(Path, "open", guard)
        result = run_profile(root, report, tmp_path / "profile")
    assert result["valid"] and result["summary"] == dict(
        businesses=1,
        successful=1,
        units=5,
        columns=12,
        rows=13,
        present_cells=11 + 7 + 12,  # CSV records + sparse OOXML cells + SQLite cells.
        headers_unresolved=3,
    )
    profile = read_business(result)
    csv = get_unit(profile, "sales")
    assert csv["header"]["status"] == "unresolved"
    assert csv["row_count"] == 5 and csv["columns"][2]["counts"] == dict(
        present=3, missing=2, null=0, empty=2, nonempty=1
    )
    assert csv["columns"][2]["ratios"]["missing"] == 0.4
    assert csv["columns"][0]["samples"][2]["value"] == "0012"
    assert csv["columns"][0]["samples"][2]["line_start"] == 3
    assert csv["columns"][1]["numeric_physical_nonempty"]["finite"] == 0
    assert csv["columns"][1]["lexical_nonempty"]["min"]["value"] == "1.234,56"
    xlsx = get_unit(profile, "Raw")
    assert [r["source_row"] for r in xlsx["row_preview"]] == [1, 3, 7, 8]
    assert xlsx["columns"][2]["counts"] == dict(
        present=2, missing=2, null=1, empty=0, nonempty=1
    )
    assert xlsx["columns"][1]["numeric_physical_nonempty"]["min_lexeme"] == "-12.50"
    assert xlsx["columns"][3]["physical_types"] == {"xlsx:d": 1}
    sql = get_unit(profile, "items'quoted")
    numeric = sql["columns"][1]["numeric_physical_nonempty"]
    assert (
        numeric["finite"],
        numeric["nonfinite"],
        numeric["min_lexeme"],
        numeric["max_lexeme"],
    ) == (2, 1, "-2.5", "9223372036854775807")
    assert sql["columns"][2]["counts"] == dict(
        present=4, missing=0, null=1, empty=1, nonempty=2
    )
    assert (
        sql["header"]["status"] == "source_schema"
        and sql["columns"][0]["declared_name"] == "code"
    )
    empty = get_unit(profile, "empty_table")
    assert empty["columns"][0]["ratios"]["null"] is None
    assert empty["columns"][0]["lexical_nonempty"]["min"] is None
    assert protected == {p: sha256(p) for p in protected}


def test_explicit_headers_are_bound_to_source_and_not_filtered(
    profiled_input, tmp_path
):
    root, _, _, report, ingestion = profiled_input
    path = annotate(
        tmp_path,
        ingestion,
        [
            dict(
                source_file="sales.csv",
                source_name="sales",
                source_kind="csv",
                rows=[2],
            ),
            dict(
                source_file="book.xlsx",
                source_name="Raw",
                source_kind="xlsx_sheet",
                rows=[1, 3],
            ),
        ],
    )
    result = run_profile(root, report, tmp_path / "profile", header_map=path)
    assert result["valid"]
    profile = read_business(result)
    csv = get_unit(profile, "sales")
    assert csv["header"]["status"] == "explicit_annotation" and csv["row_count"] == 5
    assert [c["header_cells"][0]["cell"]["value"] for c in csv["columns"]] == [
        "code",
        "value",
        "value",
    ]
    xlsx = get_unit(profile, "Raw")
    assert xlsx["columns"][1]["header_cells"] == [
        {"source_row": 1, "cell": None},
        {"source_row": 3, "cell": None},
    ]
    assert profile["provenance"]["header_map_sha256"] == sha256(path)


@pytest.mark.parametrize(
    "failure",
    [
        "stale",
        "unknown_unit",
        "absent_row",
        "duplicate",
        "unsorted",
        "bool",
        "unknown_business",
        "sqlite",
    ],
)
def test_bad_header_annotations_do_not_publish(profiled_input, tmp_path, failure):
    root, _, _, report, ingestion = profiled_input
    path = annotate(
        tmp_path,
        ingestion,
        [
            dict(
                source_file="sales.csv",
                source_name="sales",
                source_kind="csv",
                rows=[2],
            )
        ],
    )
    value = json.loads(path.read_text("utf-8"))
    entry = value["selections"][0]
    if failure == "stale":
        entry["ingest_fingerprint"] = "0" * 64
    elif failure == "unknown_unit":
        entry["source_name"] = "absent"
    elif failure == "absent_row":
        entry["rows"] = [999]
    elif failure == "duplicate":
        value["selections"].append(dict(entry))
    elif failure == "unsorted":
        entry["rows"] = [3, 2]
    elif failure == "bool":
        entry["rows"] = [True]
    elif failure == "unknown_business":
        entry["business_id"] = "absent"
    else:
        entry["source_kind"] = "sqlite_table"
    write_json(path, value)
    output = tmp_path / "profile"
    try:
        result = run_profile(root, report, output, header_map=path)
        assert not result["valid"]
    except IngestError as exc:
        assert exc.code == "profile_header_map"
    assert not list(output.rglob("schema.json"))


def test_determinism_truncation_and_consumer_query(profiled_input, tmp_path):
    root, biz, cache, report, _ = profiled_input
    long_value = "Cà phê ☕" * 10
    (biz / "sales.csv").write_text(long_value + "\n0012\n", encoding="utf-8")
    loader.run_ingest(root, cache, tmp_path / "ingest2")
    report = tmp_path / "ingest2/ingest.json"
    options = ProfileOptions(value_bytes=5, preview_columns=1)
    one = run_profile(root, report, tmp_path / "one", options)
    two = run_profile(root, report, tmp_path / "two", options)
    for kind in ("profile", "schema"):
        assert (
            one["businesses"][0][kind]["sha256"] == two["businesses"][0][kind]["sha256"]
        )
    profile = read_business(one)
    sample = get_unit(profile, "sales")["columns"][0]["samples"][0]
    assert sample["truncated"] and sample["value"] == "Cà p"
    assert sample["sha256"] == hashlib.sha256(long_value.encode()).hexdigest()
    schema = json.loads(Path(one["businesses"][0]["schema"]["path"]).read_text("utf-8"))
    table = next(t for t in schema["tables"] if t["source_name"] == "sales")
    assert table["header_status"] == "unresolved"
    with loader.connect(Path(schema["database"]), read_only=True) as con:
        value = con.execute(
            f"SELECT {loader.identifier(table['columns'][0]['sql_name'])} FROM {loader.identifier(table['sql_name'])} WHERE __row=?",
            [2],
        ).fetchone()[0]
    assert value == "0012"


@pytest.mark.parametrize(
    "limit",
    [
        "max_columns",
        "max_units",
        "max_rows_per_unit",
        "max_cells_per_business",
        "max_retained_bytes_per_unit",
        "max_report_bytes_per_business",
    ],
)
def test_profile_limits_fail_without_publishing_business(
    profiled_input, tmp_path, limit
):
    root, _, _, report, _ = profiled_input
    result = run_profile(
        root, report, tmp_path / "profile", replace(ProfileOptions(), **{limit: 1})
    )
    assert not result["valid"]
    assert not list((tmp_path / "profile").rglob("schema.json"))
    assert not list((tmp_path / "profile").rglob(".building-*"))


@pytest.mark.parametrize("failure", ["source", "database", "manifest", "report_units"])
def test_stale_and_corrupt_inputs_are_isolated(profiled_input, tmp_path, failure):
    root, biz, cache, _, _ = profiled_input
    other = root / "data/tenant_lake"
    other.mkdir()
    (other / "README.md").write_text("synthetic", encoding="utf-8")
    (other / "ok.csv").write_text("code\n0007\n", encoding="utf-8")
    ingestion = loader.run_ingest(root, cache, tmp_path / "all-ingest")
    business = next(b for b in ingestion["businesses"] if b["business_id"] == biz.name)
    if failure == "source":
        (biz / "sales.csv").write_text("DO_NOT_LEAK_SECRET", encoding="utf-8")
    elif failure == "database":
        Path(business["database"]).write_bytes(b"DO_NOT_LEAK_SECRET")
    elif failure == "manifest":
        Path(business["manifest"]).write_text("DO_NOT_LEAK_SECRET", encoding="utf-8")
    else:
        business["units"] = []
        write_json(tmp_path / "all-ingest/ingest.json", ingestion)
    result = run_profile(
        root, tmp_path / "all-ingest/ingest.json", tmp_path / "profile"
    )
    assert not result["valid"] and result["summary"]["successful"] == 1
    assert "DO_NOT_LEAK_SECRET" not in json.dumps(result)
    assert len(list((tmp_path / "profile").rglob("schema.json"))) == 1


def test_mid_scan_source_mutation_fails_atomically(
    profiled_input, tmp_path, monkeypatch
):
    root, biz, _, report, _ = profiled_input
    original = engine.profile_unit

    def changed(*args):
        result = original(*args)
        (biz / "README.md").write_text("changed", encoding="utf-8")
        return result

    monkeypatch.setattr(engine, "profile_unit", changed)
    result = run_profile(root, report, tmp_path / "profile")
    assert not result["valid"]
    assert result["businesses"][0]["errors"][0]["code"] == "profile_input_changed"
    assert not list((tmp_path / "profile").rglob("schema.json"))


def test_output_protection_and_no_accidental_gold_parse(profiled_input, tmp_path):
    root, biz, cache, report, _ = profiled_input
    for output in (biz / "out", cache / "profile", report.parent, tmp_path):
        with pytest.raises(IngestError, match="disjoint"):
            run_profile(root, report, output)
    with pytest.raises(IngestError, match="external ingest.json"):
        run_profile(root, root / "answers.jsonl", tmp_path / "profile")


def test_numeric_statistics_do_not_infer_text_or_normalize_serials():
    options = ProfileOptions(max_numeric_chars=6)
    column = ColumnStats(1, options, Retention(1000))
    for row, (value, typ) in enumerate(
        [
            ("0012", "csv:text"),
            ("1,5", "xlsx:n"),
            ("NaN", "sqlite:r"),
            ("1234567", "xlsx:n"),
            ("46000", "xlsx:n"),
            ("-2", "sqlite:i"),
        ],
        1,
    ):
        column.add(value, typ, row, {})
    stats = column.finish(6)["numeric_physical_nonempty"]
    assert {
        k: stats[k]
        for k in (
            "finite",
            "nonfinite",
            "invalid",
            "too_long",
            "min_lexeme",
            "max_lexeme",
        )
    } == dict(
        finite=2,
        nonfinite=1,
        invalid=1,
        too_long=1,
        min_lexeme="-2",
        max_lexeme="46000",
    )


def test_cli_success_and_reuse_error(profiled_input, tmp_path):
    root, _, _, report, _ = profiled_input
    command = [
        sys.executable,
        "-c",
        "from datamate.cli import main; raise SystemExit(main())",
        "profile",
        "--input",
        str(root),
        "--ingest-report",
        str(report),
        "--output",
        str(tmp_path / "profile"),
    ]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    first = subprocess.run(command, capture_output=True, encoding="utf-8", env=env)
    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout)["summary"]["successful"] == 1
    again = subprocess.run(command, capture_output=True, encoding="utf-8", env=env)
    assert (
        again.returncode == 2
        and json.loads(again.stdout)["errors"][0]["code"] == "output_overlap"
    )


def test_independent_sql_audit_detects_wrong_statistics(profiled_input, tmp_path):
    root, _, _, report, _ = profiled_input
    result = run_profile(root, report, tmp_path / "profile")
    audit = verify(root, tmp_path / "profile/profile.json", tmp_path / "audit")
    assert audit["valid"] and audit["columns"] == 12 and audit["units"] == 5
    assert audit["raw_unchanged"] and audit["cache_unchanged"]
    business = result["businesses"][0]
    path = Path(business["profile"]["path"])
    profile = json.loads(path.read_text("utf-8"))
    get_unit(profile, "sales")["columns"][0]["counts"]["missing"] += 1
    write_json(path, profile)
    business["profile"]["sha256"] = sha256(path)
    write_json(tmp_path / "profile/profile.json", result)
    with pytest.raises(ValueError, match="cell counts"):
        verify(root, tmp_path / "profile/profile.json", tmp_path / "bad-audit")
    assert not (tmp_path / "bad-audit").exists()


def test_mutation_during_output_staging_is_rejected(
    profiled_input, tmp_path, monkeypatch
):
    root, biz, _, report, _ = profiled_input
    original = Path.write_text

    def write(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        if path.name == "profile.json" and path.parent.name.startswith(".building-"):
            original(biz / "README.md", "changed during output", encoding="utf-8")
        return result

    monkeypatch.setattr(Path, "write_text", write)
    result = run_profile(root, report, tmp_path / "profile")
    assert not result["valid"]
    assert result["businesses"][0]["errors"][0]["code"] == "profile_input_changed"
    assert not list((tmp_path / "profile").rglob("schema.json"))


def test_encoding_is_explicit_evidence_not_detection(profiled_input, tmp_path):
    root, biz, cache, _, _ = profiled_input
    (biz / "sales.csv").write_bytes(b"code;label\n0012;caf\xe9\n")
    loader.run_ingest(
        root,
        cache,
        tmp_path / "latin-ingest",
        LoaderOptions(csv_encoding="latin-1", csv_delimiter=";"),
    )
    result = run_profile(
        root, tmp_path / "latin-ingest/ingest.json", tmp_path / "profile"
    )
    profile = read_business(result)
    assert profile["provenance"]["source_metadata"]["sales.csv"] == {
        "encoding": "latin-1",
        "delimiter": ";",
    }
    assert get_unit(profile, "sales")["columns"][1]["samples"][1]["value"] == "café"
    assert get_unit(profile, "sales")["header"]["status"] == "unresolved"
