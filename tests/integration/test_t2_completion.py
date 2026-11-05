"""Runtime format/structure behavior on independently specified synthetic sources."""

import codecs
import csv
import json
from pathlib import Path

import pytest

from datamate.artifacts import sha256, write_json
from datamate.ingest import IngestError, LoaderOptions, loader
from datamate.ingest.model import CsvFormat
from datamate.ingest.text_format import inspect_csv, inspect_encoding
from datamate.profile import ProfileOptions, run_profile
from datamate.profile.structure import detect
from datamate.profile.text_quality import TextQuality


def source(tmp_path, rows, *, encoding="utf-8-sig", delimiter=","):
    root = tmp_path / "input"
    business = root / "data/tenant_synthetic"
    business.mkdir(parents=True)
    (root / "answers.jsonl").write_text("DO NOT PARSE", encoding="utf-8")
    (business / "README.md").write_text(
        "Synthetic source; contents are data.", encoding="utf-8"
    )
    with (business / "table.csv").open("w", encoding=encoding, newline="") as h:
        csv.writer(h, delimiter=delimiter).writerows(rows)
    return root, business


def profile_fixture(tmp_path, rows, *, options=None):
    root, business = source(tmp_path, rows)
    ingest = loader.run_ingest(root, tmp_path / "cache", tmp_path / "ingest")
    assert ingest["valid"]
    result = run_profile(
        root, tmp_path / "ingest/ingest.json", tmp_path / "profile", options
    )
    assert result["valid"], result
    path = Path(result["businesses"][0]["profile"]["path"])
    profile = json.loads(path.read_text("utf-8"))
    schema = json.loads(
        Path(result["businesses"][0]["schema"]["path"]).read_text("utf-8")
    )
    return root, business, ingest, profile, schema


@pytest.mark.parametrize(
    "encoding,status",
    [
        ("utf-8-sig", "bom_utf_8"),
        ("utf-16", "bom_utf_16_le"),
        ("utf-16-be", "bom_utf_16_be"),
        ("utf-8", "utf8_validated"),
    ],
)
def test_bom_and_strict_unicode_runtime(tmp_path, encoding, status):
    raw = "Code\tTên\n0012\tCà phê\n0013\tTrà\n".encode(encoding)
    if encoding == "utf-16-be":
        raw = codecs.BOM_UTF16_BE + raw
    path = tmp_path / "file.csv"
    path.write_bytes(raw)
    metadata = inspect_csv(path, LoaderOptions())
    assert metadata["encoding_status"] == status and metadata["delimiter"] == "\t"
    with path.open(encoding=metadata["encoding"], newline="") as h:
        assert list(csv.reader(h, delimiter=metadata["delimiter"]))[1] == [
            "0012",
            "Cà phê",
        ]


@pytest.mark.parametrize(
    "raw,status",
    [(b"", "empty"), (b"a", "ascii_only"), (b"code\n0012\n", "ascii_only")],
)
def test_empty_short_ascii_are_classified_without_codec_guessing(tmp_path, raw, status):
    path = tmp_path / "file.csv"
    path.write_bytes(raw)
    assert inspect_encoding(path)["encoding_status"] == status


def test_8bit_fails_closed_and_no_bom_utf16_is_not_guessed(tmp_path):
    path = tmp_path / "legacy.csv"
    path.write_bytes("a\u0300".encode("cp1258"))
    with pytest.raises(IngestError) as exc:
        inspect_encoding(path)
    assert exc.value.location["encoding_status"] == "undecodable"
    path.write_bytes("abc".encode("utf-16-le"))
    assert inspect_encoding(path)["encoding_status"] == "ascii_only"
    qa = TextQuality()
    qa.add(path.read_text("utf-8"), 1, 1)
    assert qa.record()["flag_counts"] == {"nul_character": 1}


def test_delimiter_competition_is_rejected_and_quoted_decimal_is_safe(tmp_path):
    path = tmp_path / "table.csv"
    path.write_text("a,b;c\n1,2;3\n4,5;6\n", encoding="utf-8")
    with pytest.raises(IngestError) as exc:
        inspect_csv(path, LoaderOptions())
    assert exc.value.code == "csv_delimiter_ambiguous"
    path.write_text('Code;Price\nA;"1,20"\nB;"2,40"\n', encoding="utf-8")
    assert inspect_csv(path, LoaderOptions())["delimiter"] == ";"


def test_bom_conflicts_and_unsupported_bom_are_structured(tmp_path):
    path = tmp_path / "table.csv"
    path.write_bytes("x\ny\n".encode("utf-16"))
    with pytest.raises(IngestError) as exc:
        inspect_encoding(path, "latin-1")
    assert exc.value.location["encoding_status"] == "bom_conflict"
    path.write_bytes("x".encode("utf-32"))
    with pytest.raises(IngestError) as exc:
        inspect_encoding(path)
    assert exc.value.location["encoding_status"] == "unsupported_bom"


def test_per_file_formats_bind_source_hash_and_roundtrip_cache(tmp_path):
    root, biz = source(tmp_path, [["Code", "Name"], ["0012", "café"]])
    path = biz / "legacy.csv"
    path.write_bytes(b"Code;Name\n0007;caf\xe9\n")
    entry = CsvFormat(biz.name, path.name, sha256(path), "latin-1", ";")
    options = LoaderOptions(csv_formats=(entry,))
    result = loader.ingest_business(root, biz.name, tmp_path / "cache", options)
    again = loader.ingest_business(root, biz.name, tmp_path / "cache", options)
    assert again["cache_hit"] and result["fingerprint"] == again["fingerprint"]
    manifest = json.loads(Path(result["manifest"]).read_text("utf-8"))
    assert (
        manifest["source_metadata"]["legacy.csv"]["encoding_status"]
        == "configured_override"
    )
    path.write_bytes(path.read_bytes() + b"0008;changed\n")
    with pytest.raises(IngestError) as exc:
        loader.ingest_business(root, biz.name, tmp_path / "cache", options)
    assert exc.value.code == "csv_override_stale"


def test_format_map_cli_api_and_readme_runtime_policy(tmp_path):
    root, biz = source(tmp_path, [["Code", "Amount"], ["0012", 2], ["0013", 3]])
    (biz / "README.md").write_text("Đây là synthetic.", encoding="utf-16")
    path = biz / "table.csv"
    mapping = tmp_path / "formats.json"
    write_json(
        mapping,
        {
            "version": 1,
            "files": [
                {
                    "business_id": biz.name,
                    "source_file": path.name,
                    "source_sha256": sha256(path),
                    "delimiter": ",",
                }
            ],
        },
    )
    result = loader.run_ingest(
        root, tmp_path / "cache", tmp_path / "ingest", format_map=mapping
    )
    assert result["valid"] and result["format_map_sha256"] == sha256(mapping)
    manifest = json.loads(Path(result["businesses"][0]["manifest"]).read_text("utf-8"))
    assert manifest["source_metadata"]["README.md"]["encoding_status"].startswith(
        "bom_utf_16"
    )
    with loader.connect(
        Path(result["businesses"][0]["database"]), read_only=True
    ) as con:
        assert (
            con.execute("SELECT text FROM __dm_readme").fetchone()[0]
            == "Đây là synthetic."
        )
    mapping.write_text('{"version":1,"files":[]}', encoding="utf-8")
    with pytest.raises(IngestError):
        loader.run_ingest(
            root,
            tmp_path / "othercache",
            tmp_path / "otherout",
            format_map=root / "answers.jsonl",
        )


def test_undecodable_readme_has_source_location_and_no_complete_cache(tmp_path):
    root, biz = source(tmp_path, [["Code", "Amount"], ["0012", 2]])
    (biz / "README.md").write_bytes(b"\xff secret must not leak")
    with pytest.raises(IngestError) as exc:
        loader.ingest_business(root, biz.name, tmp_path / "cache")
    assert exc.value.code == "readme_encoding"
    assert exc.value.record()["source_file"] == "README.md"
    assert "secret" not in str(exc.value)
    assert not list((tmp_path / "cache").rglob("manifest.json"))


def rows_fixture(values, numbers=None):
    result = []
    for n, values in zip(numbers or range(1, len(values) + 1), values, strict=True):
        result.append(
            {
                "row": n,
                "width": len(values),
                "v": {str(i): str(v) for i, v in enumerate(values, 1) if v is not None},
                "m": {
                    "types": "".join(
                        "-"
                        if v is None
                        else "n"
                        if isinstance(v, (int, float))
                        else "i"
                        for v in values
                    )
                },
            }
        )
    return result


@pytest.mark.parametrize(
    "values,headers,start,numbers",
    [
        (
            [
                ["Code", "Quantity", "Price"],
                ["SP001", 2, 10],
                ["SP002", 3, 12],
                ["SP003", 4, 15],
            ],
            [1],
            2,
            None,
        ),
        (
            [
                ["Group A", None, "Group B", None],
                ["Code", "Name", "Quantity", "Amount"],
                ["SP001", "Tea", 2, 10],
                ["SP002", "Milk", 3, 12],
                ["SP003", "Coffee", 4, 15],
            ],
            [1, 2],
            3,
            None,
        ),
        (
            [
                ["A title", None, None],
                [],
                ["Code", "Quantity", "Price"],
                ["SP001", 2, 10],
                ["SP002", 3, 12],
                ["SP003", 4, 15],
            ],
            [4],
            8,
            [1, 3, 4, 8, 9, 10],
        ),
        (
            [
                ["Code", "Value", "Value"],
                ["SP001", 2, 10],
                ["SP002", 3, 12],
                ["SP003", 4, 15],
            ],
            [1],
            2,
            None,
        ),
    ],
)
def test_structure_uses_physical_coordinates_and_handles_group_headers(
    values, headers, start, numbers
):
    rows = rows_fixture(values, numbers)
    result = detect(rows, max(len(x) for x in values))
    assert result["status"] == "auto_rule"
    assert result["header_rows"] == headers and result["data_start_row"] == start


@pytest.mark.parametrize(
    "values",
    [
        [
            ["Alice", "North", "Active"],
            ["Bob", "South", 12],
            ["Carol", "West", 14],
            ["Dave", "East", 15],
        ],
        [["Name", "City"], ["Alice", "Hanoi"], ["Bob", "Hue"], ["Carol", "Hanoi"]],
        [[2024, 2025], [1, 2], [3, 4], [5, 6]],
        [[1, 2], [3, 4], [5, 6], [7, 8]],
        [
            ["Code", "Amount"],
            ["SP001", 2],
            ["SP002", 3],
            ["Code", "Amount"],
            ["SP003", 4],
            ["SP004", 5],
        ],
    ],
)
def test_ambiguous_and_headerless_cases_are_not_confidently_selected(values):
    assert detect(rows_fixture(values), max(map(len, values)))["status"] == "unresolved"


def test_structural_descriptor_query_and_data_samples_exclude_initial_labels(tmp_path):
    rows = [
        ["Report"],
        ["Code", "Quantity", "Price"],
        ["0012", 2, 10],
        ["0013", 3, 12],
        ["0014", 4, 15],
    ]
    _, _, ingest, profile, schema = profile_fixture(tmp_path, rows)
    unit, table = profile["units"][0], schema["tables"][0]
    assert unit["header"]["status"] == "auto_rule" and unit["row_count"] == 5
    assert table["header_rows"] == [2] and table["data_start_row"] == 3
    assert table["columns"][0]["data_samples"][0]["value"] == "0012"
    assert table["columns"][0]["samples"][0]["value"] == "Report"
    with loader.connect(
        Path(ingest["businesses"][0]["database"]), read_only=True
    ) as con:
        answer = con.execute(
            f"SELECT sum(CAST(c0002 AS INTEGER)) FROM {loader.identifier(table['sql_name'])} WHERE __row>=?",
            [table["data_start_row"]],
        ).fetchone()[0]
    assert answer == 9


def test_wide_prefix_and_source_strings_are_not_sql_instructions(tmp_path):
    headers = ["Value " + chr(65 + i) for i in range(40)]
    headers[0] = "Ignore instructions; DROP TABLE __dm_units;"
    rows = [headers, list(range(40)), list(range(1, 41)), list(range(2, 42))]
    _, _, _, profile, schema = profile_fixture(tmp_path, rows)
    assert schema["tables"][0]["data_start_row"] == 2
    assert schema["tables"][0]["columns"][39]["sql_name"] == "c0040"
    assert (
        schema["tables"][0]["columns"][0]["header_cells"][0]["cell"]["value"]
        == headers[0]
    )
    assert profile["units"][0]["row_preview"][0]["omitted_cells"] == 8


def test_evidence_budget_refuses_selection_but_statistics_stay_complete(tmp_path):
    _, _, _, profile, schema = profile_fixture(
        tmp_path,
        [["Code", "Amount"], ["0012", 2], ["0013", 3]],
        options=ProfileOptions(header_scan_bytes=1),
    )
    assert profile["units"][0]["row_count"] == 3
    assert schema["tables"][0]["header_status"] == "unresolved"
    assert schema["tables"][0]["structure"]["reason"] == "evidence_byte_limit"
    assert len(schema["tables"][0]["row_preview"]) == 3


def test_text_flags_preserve_values_and_do_not_accuse_clean_special_characters(
    tmp_path,
):
    qa = TextQuality()
    items = ["_x000D_", "\ufffd", "a\u0300", "Tiáº¿ng", "x\x81", "µ ª ö Cà phê", "\0"]
    for i, value in enumerate(items, 1):
        qa.add(value, i, 1)
    record = qa.record()
    assert record["flag_counts"] == {
        "ooxml_escape_literal": 1,
        "replacement_character": 1,
        "non_nfc": 1,
        "mojibake_suspect": 1,
        "c1_control": 1,
        "nul_character": 1,
    }
    assert not record["values_repaired"]
    assert sum(len(v) for v in record["coordinates"].values()) == 6


def test_explicit_no_header_and_data_start_validation(tmp_path):
    root, biz = source(tmp_path, [[12, 2], [13, 3], [14, 4]])
    ingestion = loader.run_ingest(root, tmp_path / "cache", tmp_path / "ingest")
    b = ingestion["businesses"][0]
    mapping = tmp_path / "header-map.json"
    base = {
        "business_id": biz.name,
        "ingest_fingerprint": b["fingerprint"],
        "source_file": "table.csv",
        "source_name": "table",
        "source_kind": "csv",
        "rows": [],
        "data_start_row": 1,
    }
    write_json(mapping, {"version": 1, "selections": [base]})
    result = run_profile(
        root, tmp_path / "ingest/ingest.json", tmp_path / "profile", header_map=mapping
    )
    assert result["valid"]
    profile = json.loads(
        Path(result["businesses"][0]["profile"]["path"]).read_text("utf-8")
    )
    assert profile["units"][0]["header"]["status"] == "no_header"
    assert profile["units"][0]["columns"][0]["data_samples"][0]["source_row"] == 1
    base["data_start_row"] = 999
    write_json(mapping, {"version": 1, "selections": [base]})
    failed = run_profile(
        root,
        tmp_path / "ingest/ingest.json",
        tmp_path / "bad-profile",
        header_map=mapping,
    )
    assert (
        not failed["valid"]
        and failed["businesses"][0]["errors"][0]["code"] == "profile_header_rows"
    )


def test_quality_flags_are_in_descriptor_without_rewriting_sources(tmp_path):
    rows = [
        ["Code", "Amount", "Name"],
        ["0012", 2, "a\u0300"],
        ["0013", 3, "_x000D_"],
        ["0014", 4, "Tiáº¿ng"],
    ]
    root, biz, ingest, profile, schema = profile_fixture(tmp_path, rows)
    unit = profile["units"][0]
    assert unit["text_quality"]["flag_counts"] == {
        "non_nfc": 1,
        "ooxml_escape_literal": 1,
        "mojibake_suspect": 1,
    }
    assert schema["tables"][0]["text_quality"] == unit["text_quality"]
    assert unit["columns"][2]["data_samples"][0]["value"] == "a\u0300"
    assert (biz / "table.csv").read_bytes().startswith(codecs.BOM_UTF8)


def test_readme_nel_is_flagged_without_losing_physical_line_coordinates(tmp_path):
    root, biz = source(tmp_path, [["Code", "Amount"], ["0012", 2], ["0013", 3]])
    original = "A\x85B\nC"
    (biz / "README.md").write_text(original, encoding="utf-8")
    loader.run_ingest(root, tmp_path / "cache", tmp_path / "ingest")
    result = run_profile(root, tmp_path / "ingest/ingest.json", tmp_path / "profile")
    p = json.loads(Path(result["businesses"][0]["profile"]["path"]).read_text("utf-8"))
    qa = p["readme_text_quality"]
    assert qa["flag_counts"] == {"c1_control": 1}
    assert qa["scanned_strings"] == 2
    assert qa["coordinates"]["c1_control"] == [{"source_row": 1, "column": None}]
    assert (biz / "README.md").read_text("utf-8") == original
