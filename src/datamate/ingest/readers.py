"""Streaming raw readers. Unit iterators must be exhausted before advancing."""

import base64
import csv
import json
import posixpath
import re
import sqlite3
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from datamate.ingest.model import IngestError, LoaderOptions, RawRow, RawUnit
from datamate.ingest.text_format import inspect_csv

S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
TYPE_CODES = {
    "n": "n",
    "inlineStr": "i",
    "s": "s",
    "str": "x",
    "b": "b",
    "e": "e",
    "d": "d",
}


def string_text(element, namespace):
    if element is None:
        return ""
    parts = []
    for child in element:
        if child.tag == namespace + "t":
            parts.append(child.text or "")
        elif child.tag == namespace + "r":
            text = child.find(namespace + "t")
            parts.append(text.text or "" if text is not None else "")
    return "".join(parts)


def dump(value) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def check_row(row: RawRow, options: LoaderOptions) -> None:
    if row.width > options.max_columns:
        raise IngestError("column_limit", "Column limit exceeded", row=row.number)
    for i, value in row.values.items():
        if i < 1 or i > row.width:
            raise IngestError(
                "cell_coordinate", "Invalid cell coordinate", row=row.number
            )
        if value is not None and len(value.encode("utf-8")) > options.max_cell_bytes:
            raise IngestError(
                "cell_limit", "Cell size limit exceeded", row=row.number, column=i
            )


def read_csv(path: Path, options: LoaderOptions):
    metadata = inspect_csv(path, options)

    def rows():
        limit = csv.field_size_limit()
        csv.field_size_limit(options.max_cell_bytes)
        try:
            with path.open(
                encoding=metadata["encoding"], errors="strict", newline=""
            ) as h:
                reader = csv.reader(h, delimiter=metadata["delimiter"], strict=True)
                previous = 0
                for number, values in enumerate(reader, 1):
                    yield RawRow(
                        number,
                        len(values),
                        dict(enumerate(values, 1)),
                        {"line_start": previous + 1, "line_end": reader.line_num},
                    )
                    previous = reader.line_num
        except UnicodeError as exc:
            raise IngestError(
                "csv_encoding", "CSV cannot be decoded with configured encoding"
            ) from exc
        except csv.Error as exc:
            raise IngestError(
                "csv_parse", "Malformed CSV or CSV field limit exceeded"
            ) from exc
        finally:
            csv.field_size_limit(limit)

    yield RawUnit(path.stem, "csv", rows(), source_metadata=metadata)


class SafeXML:
    def __init__(self, handle, limit: int):
        self.handle = handle
        self.limit = limit
        self.total = 0
        self.tail = b""

    def read(self, size=-1):
        chunk = self.handle.read(size)
        self.total += len(chunk)
        if self.total > self.limit:
            raise IngestError("xml_limit", "XML size limit exceeded")
        scan = (self.tail + chunk).replace(b"\0", b"").upper()
        if b"<!DOCTYPE" in scan or b"<!ENTITY" in scan:
            raise IngestError(
                "xml_unsafe", "DTD and entity declarations are not supported"
            )
        self.tail = (self.tail + chunk)[-48:]
        return chunk


def xml_small(z: ZipFile, name: str, options: LoaderOptions):
    with z.open(name) as h:
        return ET.parse(SafeXML(h, options.max_metadata_bytes)).getroot()


def column(ref: str) -> tuple[int, int]:
    match = re.fullmatch(r"([A-Z]+)([1-9][0-9]*)", ref)
    if not match:
        raise IngestError("cell_coordinate", "Invalid worksheet cell coordinate")
    index = 0
    for char in match[1]:
        index = index * 26 + ord(char) - 64
    return index, int(match[2])


def read_xlsx(path: Path, options: LoaderOptions):
    with ZipFile(path) as z:
        infos = z.infolist()
        names = {i.filename for i in infos}
        if len(names) != len(infos):
            raise IngestError("xlsx_members", "Duplicate ZIP member names")
        if sum(i.file_size for i in infos) > options.max_zip_bytes:
            raise IngestError("zip_limit", "Expanded workbook exceeds size limit")
        if any(i.flag_bits & 1 or i.file_size > options.max_xml_bytes for i in infos):
            raise IngestError("zip_limit", "Encrypted or oversized workbook entry")
        workbook = xml_small(z, "xl/workbook.xml", options)
        namespace = workbook.tag.removesuffix("workbook")
        if namespace not in {S, "{http://purl.oclc.org/ooxml/spreadsheetml/main}"}:
            raise IngestError("xlsx_namespace", "Unsupported workbook XML namespace")
        ns = namespace
        relation_ns = (
            R
            if namespace == S
            else "{http://purl.oclc.org/ooxml/officeDocument/relationships}"
        )
        rels = {
            e.attrib["Id"]: e.attrib
            for e in xml_small(z, "xl/_rels/workbook.xml.rels", options)
        }
        shared = []
        if "xl/sharedStrings.xml" in names:
            with z.open("xl/sharedStrings.xml") as h:
                shared_root = None
                for event, e in ET.iterparse(
                    SafeXML(h, options.max_shared_strings_bytes),
                    events=("start", "end"),
                ):
                    if shared_root is None:
                        shared_root = e
                    if event == "end" and e.tag == ns + "si":
                        text = string_text(e, ns)
                        if len(text.encode("utf-8")) > options.max_cell_bytes:
                            raise IngestError(
                                "cell_limit", "Shared string size limit exceeded"
                            )
                        shared.append(text)
                        e.clear()
                        shared_root.remove(e)
        prop = workbook.find(ns + "workbookPr")
        source_meta = {
            "format": "OOXML",
            "workbook_properties": prop.attrib if prop is not None else {},
            "shared_string_count": len(shared),
            "package_members": sorted(names),
        }
        if "xl/styles.xml" in names:
            styles = xml_small(z, "xl/styles.xml", options)
            source_meta["styles_xml"] = ET.tostring(styles, encoding="unicode")
        seen_names = set()
        sheets = workbook.find(ns + "sheets")
        if sheets is None or not len(sheets):
            raise IngestError("xlsx_sheets", "Workbook contains no worksheets")
        for sheet in sheets:
            name = sheet.attrib["name"]
            if name in seen_names:
                raise IngestError("xlsx_sheets", "Duplicate worksheet name")
            seen_names.add(name)
            rel = rels[sheet.attrib[relation_ns + "id"]]
            if rel.get("TargetMode") == "External" or not rel.get("Type", "").endswith(
                "/worksheet"
            ):
                raise IngestError(
                    "xlsx_relationship",
                    "Only internal worksheet relationships are supported",
                    unit=name,
                )
            target = rel["Target"]
            member = posixpath.normpath(
                target.lstrip("/") if target.startswith("/") else "xl/" + target
            )
            if not member.startswith("xl/") or "\\" in member or member not in names:
                raise IngestError(
                    "xlsx_relationship",
                    "Worksheet relationship escapes package or is missing",
                    unit=name,
                )
            meta = {"attributes": dict(sheet.attrib), "merges": []}

            def rows(member=member, meta=meta):
                previous = 0
                with z.open(member) as h:
                    sheet_data = None
                    for event, e in ET.iterparse(
                        SafeXML(h, options.max_xml_bytes), events=("start", "end")
                    ):
                        if event == "start":
                            if e.tag == ns + "sheetData":
                                sheet_data = e
                            continue
                        if e.tag == ns + "dimension":
                            meta["declared_dimension"] = e.attrib.get("ref")
                        elif e.tag == ns + "mergeCell":
                            meta["merges"].append(dict(e.attrib))
                        elif e.tag == ns + "row":
                            number = int(e.attrib["r"])
                            if number <= previous or number > 1048576:
                                raise IngestError(
                                    "row_coordinate",
                                    "Worksheet rows must have increasing coordinates",
                                    row=number,
                                )
                            previous = number
                            values, types, styles, formulas, raw_shared, other = (
                                {},
                                {},
                                {},
                                {},
                                {},
                                {},
                            )
                            for cell in e.findall(ns + "c"):
                                i, rn = column(cell.attrib["r"])
                                if rn != number or i in types:
                                    raise IngestError(
                                        "cell_coordinate",
                                        "Duplicate or inconsistent worksheet cell coordinate",
                                        row=number,
                                        column=i,
                                    )
                                if i > options.max_columns:
                                    raise IngestError(
                                        "column_limit",
                                        "Worksheet column limit exceeded",
                                        row=number,
                                    )
                                typ = cell.attrib.get("t", "n")
                                if typ not in TYPE_CODES:
                                    raise IngestError(
                                        "xlsx_cell_type",
                                        "Unsupported worksheet cell type",
                                        row=number,
                                        column=i,
                                    )
                                types[i] = TYPE_CODES[typ]
                                value = cell.find(ns + "v")
                                text = value.text if value is not None else None
                                if typ == "inlineStr":
                                    text = string_text(cell.find(ns + "is"), ns)
                                elif typ == "s":
                                    if (
                                        text is None
                                        or not text.isdigit()
                                        or int(text) >= len(shared)
                                    ):
                                        raise IngestError(
                                            "xlsx_shared_string",
                                            "Invalid shared string reference",
                                            row=number,
                                            column=i,
                                        )
                                    raw_shared[str(i)] = text
                                    text = shared[int(text)]
                                values[i] = text
                                if "s" in cell.attrib:
                                    styles[str(i)] = cell.attrib["s"]
                                formula = cell.find(ns + "f")
                                if formula is not None:
                                    formulas[str(i)] = {
                                        "text": formula.text,
                                        "attributes": dict(formula.attrib),
                                    }
                                attrs = {
                                    k: v
                                    for k, v in cell.attrib.items()
                                    if k not in {"r", "t", "s"}
                                }
                                if attrs:
                                    other[str(i)] = attrs
                            width = max(types, default=0)
                            cell_meta = {
                                "types": "".join(
                                    types.get(i, "-") for i in range(1, width + 1)
                                )
                            }
                            for key, item in [
                                ("styles", styles),
                                ("formulas", formulas),
                                ("shared", raw_shared),
                                ("attributes", other),
                            ]:
                                if item:
                                    cell_meta[key] = item
                            attrs = {k: v for k, v in e.attrib.items() if k != "r"}
                            if attrs:
                                cell_meta["row_attributes"] = attrs
                            yield RawRow(number, width, values, cell_meta)
                            e.clear()
                            if sheet_data is None:
                                raise IngestError(
                                    "xlsx_structure",
                                    "Rows must occur inside worksheet sheetData",
                                )
                            sheet_data.remove(e)

            yield RawUnit(name, "xlsx_sheet", rows(), meta, source_meta)


def read_sqlite(path: Path, options: LoaderOptions):
    if any(
        Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")
    ):
        raise IngestError(
            "sqlite_sidecar",
            "SQLite sidecar requires an explicit checkpointed snapshot",
        )
    con = sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        con.execute("PRAGMA query_only=ON")
        con.execute("PRAGMA trusted_schema=OFF")
        deadline = time.monotonic() + options.sqlite_timeout_seconds
        con.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
        catalog = con.execute(
            "SELECT name,type,sql FROM sqlite_master WHERE type IN ('table','view') ORDER BY name"
        ).fetchall()
        table_types = {
            r[1]: r[2]
            for r in con.execute("PRAGMA table_list").fetchall()
            if r[0] == "main"
        }
        for name, kind, sql in catalog:
            if name.startswith("sqlite_"):
                continue
            if (
                kind != "table"
                or table_types.get(name) != "table"
                or re.search(r"\bCREATE\s+VIRTUAL\s+TABLE\b", sql or "", re.I)
            ):
                raise IngestError(
                    "sqlite_object",
                    "Views and virtual tables are not executed",
                    unit=name,
                )
            quoted = '"' + name.replace('"', '""') + '"'
            columns = con.execute("PRAGMA table_xinfo(" + quoted + ")").fetchall()
            if any(c[6] for c in columns):
                raise IngestError(
                    "sqlite_generated",
                    "Generated or hidden columns require an explicit reader",
                    unit=name,
                )

            def rows(quoted=quoted):
                for number, row in enumerate(con.execute("SELECT * FROM " + quoted), 1):
                    values, types = {}, []
                    for i, value in enumerate(row, 1):
                        if value is None:
                            types.append("0")
                            values[i] = None
                        elif isinstance(value, bytes):
                            types.append("b")
                            values[i] = base64.b64encode(value).decode("ascii")
                        elif isinstance(value, int):
                            types.append("i")
                            values[i] = str(value)
                        elif isinstance(value, float):
                            types.append("r")
                            values[i] = repr(value)
                        else:
                            types.append("t")
                            values[i] = value
                    yield RawRow(number, len(row), values, {"types": "".join(types)})

            yield RawUnit(
                name,
                "sqlite_table",
                rows(),
                {
                    "columns": columns,
                    "ddl": sql,
                    "foreign_keys": con.execute(
                        "PRAGMA foreign_key_list(" + quoted + ")"
                    ).fetchall(),
                },
                {
                    "sqlite_version": sqlite3.sqlite_version,
                    "row_order": "scan ordinal, not a declared business key",
                },
            )
    finally:
        con.close()


def read_source(path: Path, options: LoaderOptions):
    try:
        yield from {".csv": read_csv, ".xlsx": read_xlsx, ".sqlite": read_sqlite}[
            path.suffix.lower()
        ](path, options)
    except IngestError:
        raise
    except (
        ET.ParseError,
        BadZipFile,
        KeyError,
        IndexError,
        ValueError,
        sqlite3.Error,
        UnicodeError,
        OSError,
    ) as exc:
        raise IngestError(
            "source_read", "Source cannot be read with the supported raw format"
        ) from exc
