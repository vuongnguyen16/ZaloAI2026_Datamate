"""Atomic, content-addressed raw ingestion; never executes dataset SQL/text."""

import csv
import hashlib
import json
import os
import platform
import re
import shutil
import sqlite3
import tempfile
import time
import xml.etree.ElementTree as ET
from contextlib import closing
from dataclasses import asdict, replace
from pathlib import Path
from zipfile import BadZipFile

import duckdb

from datamate.artifacts import sha256, write_json
from datamate.ingest.model import CsvFormat, IngestError, LoaderOptions
from datamate.ingest.readers import check_row, dump, read_source
from datamate.ingest.text_format import inspect_encoding

SCHEMA_VERSION = 1
TABLE_SUFFIXES = {".csv", ".xlsx", ".sqlite"}


def identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def code_hash() -> str:
    files = {p.name: sha256(p) for p in sorted(Path(__file__).parent.glob("*.py"))}
    return hashlib.sha256(dump(files).encode()).hexdigest()


def is_link(path: Path) -> bool:
    return path.is_symlink() or (
        path.exists() and bool(getattr(path.lstat(), "st_file_attributes", 0) & 0x400)
    )


def disjoint(a: Path, b: Path) -> bool:
    return not (a == b or a.is_relative_to(b) or b.is_relative_to(a))


def roots(input_dir: Path, cache_root: Path) -> tuple[Path, Path]:
    source = input_dir.resolve(strict=True)
    cache = cache_root.resolve()
    if not source.is_dir() or not disjoint(source, cache):
        raise IngestError(
            "output_overlap", "Cache and input directories must be disjoint"
        )
    return source, cache


def business_path(source: Path, business_id: str) -> Path:
    if (
        not isinstance(business_id, str)
        or not business_id.strip()
        or business_id in {".", ".."}
        or any(c in business_id for c in "/\\:\0")
    ):
        raise IngestError("business_id", "Invalid business ID")
    path = source / "data" / business_id
    if (
        is_link(source / "data")
        or not path.is_dir()
        or is_link(path)
        or not path.resolve().is_relative_to(source)
    ):
        raise IngestError("input_path", "Business directory is missing or aliased")
    return path


def snapshot(business: Path, options: LoaderOptions) -> list[dict]:
    if not (business / "README.md").is_file():
        raise IngestError("missing_readme", "Business README.md is required")
    files = []
    for path in sorted(business.rglob("*")):
        if is_link(path) or not path.resolve().is_relative_to(business):
            raise IngestError("input_alias", "Business input aliases are not supported")
        if path.is_dir():
            continue
        relative = path.relative_to(business).as_posix()
        if relative.endswith(("-wal", "-shm", "-journal")):
            raise IngestError(
                "sqlite_sidecar",
                "SQLite sidecar requires an explicit checkpointed snapshot",
                source_file=relative,
            )
        if relative != "README.md" and path.suffix.lower() not in TABLE_SUFFIXES:
            raise IngestError(
                "unsupported_file",
                "Unsupported file in business input",
                source_file=relative,
            )
        if not path.is_file() or path.stat().st_size > options.max_source_bytes:
            raise IngestError(
                "source_limit",
                "Source is not a regular file or exceeds size limit",
                source_file=relative,
            )
        if relative == "README.md" and path.stat().st_size > options.max_metadata_bytes:
            raise IngestError("metadata_limit", "README exceeds metadata size limit")
        files.append(
            {
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    if sum(f["size_bytes"] for f in files) > options.max_business_bytes:
        raise IngestError("business_limit", "Business source size limit exceeded")
    if not any(Path(f["path"]).suffix.lower() in TABLE_SUFFIXES for f in files):
        raise IngestError("missing_tables", "Business has no supported table source")
    return files


def connect(path: Path, *, read_only=False):
    config = {
        "threads": 2,
        "memory_limit": "256MB",
        "autoinstall_known_extensions": False,
        "autoload_known_extensions": False,
    }
    if read_only:
        config["enable_external_access"] = False
    return duckdb.connect(str(path), read_only=read_only, config=config)


def frame_update(h, number: int, width: int, payload: str):
    h.update(
        str(number).encode()
        + b"\0"
        + str(width).encode()
        + b"\0"
        + payload.encode("utf-8")
        + b"\n"
    )


def database_frame_hash(con, storage: str) -> str:
    h = hashlib.sha256()
    cur = con.execute(
        f"SELECT __row, __width, CAST(__payload AS VARCHAR) FROM {identifier(storage)} ORDER BY __row"
    )
    while rows := cur.fetchmany(1024):
        for number, width, payload in rows:
            frame_update(h, number, width, payload)
    return h.hexdigest()


def write_unit(con, stage: Path, relative: str, unit, options: LoaderOptions):
    token = hashlib.sha256(dump([relative, unit.kind, unit.name]).encode()).hexdigest()[
        :24
    ]
    storage, view = "rows_" + token, "raw_" + token
    spool = stage / "unit.csv"
    count, nonempty, width, previous = 0, 0, 0, 0
    if unit.kind == "sqlite_table":
        width = len(unit.metadata["columns"])
    h = hashlib.sha256()
    with closing(unit.rows), spool.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        for row in unit.rows:
            count += 1
            if count > options.max_rows:
                raise IngestError("row_limit", "Row limit exceeded", row=row.number)
            if row.number <= previous:
                raise IngestError(
                    "row_coordinate",
                    "Source row coordinates must increase",
                    row=row.number,
                )
            previous = row.number
            check_row(row, options)
            width = max(width, row.width)
            nonempty += any(v is not None and v != "" for v in row.values.values())
            payload = dump(
                {"v": {str(i): v for i, v in row.values.items()}, "m": row.metadata}
            )
            if len(payload.encode("utf-8")) > options.max_row_bytes:
                raise IngestError(
                    "row_size_limit",
                    "Serialized row size limit exceeded",
                    row=row.number,
                )
            writer.writerow((row.number, row.width, payload))
            frame_update(h, row.number, row.width, payload)
            if handle.tell() > options.max_staging_bytes:
                raise IngestError(
                    "staging_limit", "Staging size limit exceeded", row=row.number
                )
    if width > options.max_columns:
        raise IngestError("column_limit", "Column limit exceeded")
    if count:
        con.execute(
            f"""CREATE TABLE {identifier(storage)} AS
            SELECT * FROM read_csv(?, columns={{'__row':'BIGINT','__width':'INTEGER','__payload':'JSON'}},
                auto_detect=false, header=false, delim=',', quote='"', escape='"',
                allow_quoted_nulls=false, nullstr='', parallel=false, strict_mode=true,
                max_line_size=?, buffer_size=?)""",
            [
                str(spool),
                options.max_row_bytes * 2 + 1024,
                (options.max_row_bytes * 2 + 1024) * 4,
            ],
        )
    else:
        con.execute(
            f"CREATE TABLE {identifier(storage)} (__row BIGINT, __width INTEGER, __payload JSON)"
        )
    spool.unlink()
    if database_frame_hash(con, storage) != h.hexdigest():
        raise IngestError(
            "preservation", "DuckDB frame read-back does not match the raw reader"
        )
    columns = ["__row", "__width", "json_extract(__payload, '$.m') AS __metadata"]
    columns += [
        f"json_extract_string(__payload, '$.v.\"{i}\"') AS c{i:04d}"
        for i in range(1, width + 1)
    ]
    con.execute(
        f"CREATE VIEW {identifier(view)} AS SELECT {', '.join(columns)} FROM {identifier(storage)}"
    )
    return {
        "source_file": relative,
        "source_kind": unit.kind,
        "source_name": unit.name,
        "storage_table": storage,
        "view_name": view,
        "row_count": count,
        "nonempty_rows": nonempty,
        "max_width": width,
        "frame_sha256": h.hexdigest(),
        "metadata": unit.metadata,
    }


def validate_cache(generation: Path, signature: dict, fingerprint: str) -> dict:
    try:
        if is_link(generation) or not generation.is_dir():
            raise ValueError
        manifest_path = generation / "manifest.json"
        database = generation / "raw.duckdb"
        if is_link(manifest_path) or is_link(database):
            raise ValueError
        manifest = json.loads(manifest_path.read_text("utf-8"))
        if (
            manifest["signature"] != signature
            or manifest["fingerprint"] != fingerprint
            or manifest["schema_version"] != SCHEMA_VERSION
        ):
            raise ValueError
        if sha256(database) != manifest["database_sha256"]:
            raise ValueError
        units = manifest["units"]
        with connect(database, read_only=True) as con:
            catalog = con.execute(
                "SELECT source_file,source_name,storage_table,view_name,row_count,max_width,frame_sha256 FROM __dm_units ORDER BY storage_table"
            ).fetchall()
            expected = sorted(
                [
                    (
                        u["source_file"],
                        u["source_name"],
                        u["storage_table"],
                        u["view_name"],
                        u["row_count"],
                        u["max_width"],
                        u["frame_sha256"],
                    )
                    for u in units
                ],
                key=lambda u: u[2],
            )
            if catalog != expected:
                raise ValueError
            for u in units:
                if not re.fullmatch(
                    r"rows_[0-9a-f]{24}", u["storage_table"]
                ) or not re.fullmatch(r"raw_[0-9a-f]{24}", u["view_name"]):
                    raise ValueError
                if (
                    con.execute(
                        f"SELECT count(*) FROM {identifier(u['storage_table'])}"
                    ).fetchone()[0]
                    != u["row_count"]
                ):
                    raise ValueError
                schema = con.execute(
                    f"DESCRIBE {identifier(u['view_name'])}"
                ).fetchall()
                if [c[0] for c in schema] != ["__row", "__width", "__metadata"] + [
                    f"c{i:04d}" for i in range(1, u["max_width"] + 1)
                ]:
                    raise ValueError
        return manifest
    except (OSError, ValueError, KeyError, TypeError, duckdb.Error) as exc:
        raise IngestError(
            "cache_corrupt",
            "Cache generation failed integrity checks; use a new cache directory",
        ) from exc


def _ingest_business(
    input_dir: Path,
    business_id: str,
    cache_root: Path,
    options: LoaderOptions | None = None,
) -> dict:
    options = options or LoaderOptions()
    source, cache = roots(Path(input_dir), Path(cache_root))
    business = business_path(source, business_id)
    options = replace(
        options,
        csv_formats=tuple(
            f for f in options.csv_formats if f.business_id == business_id
        ),
    )
    files = snapshot(business, options)
    for override in options.csv_formats:
        if not any(
            f["path"] == override.source_file and f["sha256"] == override.source_sha256
            for f in files
        ):
            raise IngestError(
                "csv_override_stale",
                "CSV format override references an unknown or changed source",
            )
    signature = {
        "schema_version": SCHEMA_VERSION,
        "business_id": business_id,
        "files": files,
        "options": json.loads(dump(asdict(options))),
        "loader_code_sha256": code_hash(),
        "duckdb_version": duckdb.__version__,
        "python_version": platform.python_version(),
        "sqlite_version": sqlite3.sqlite_version,
    }
    fingerprint = hashlib.sha256(dump(signature).encode()).hexdigest()
    namespace = cache / ("b_" + hashlib.sha256(business_id.encode()).hexdigest()[:24])
    namespace.mkdir(parents=True, exist_ok=True)
    if not namespace.resolve().is_relative_to(cache) or is_link(namespace):
        raise IngestError("cache_path", "Cache namespace is aliased")
    generation = namespace / fingerprint
    started = time.perf_counter()

    def result(manifest, hit):
        return {
            "valid": True,
            "business_id": business_id,
            "fingerprint": fingerprint,
            "cache_hit": hit,
            "database": str(generation / "raw.duckdb"),
            "manifest": str(generation / "manifest.json"),
            "files": len(files),
            "units": manifest["units"],
            "rows": sum(u["row_count"] for u in manifest["units"]),
            "nonempty_rows": sum(u["nonempty_rows"] for u in manifest["units"]),
            "duration_seconds": time.perf_counter() - started,
        }

    if generation.exists():
        manifest = validate_cache(generation, signature, fingerprint)
        if snapshot(business, options) != files:
            raise IngestError(
                "input_changed", "Business inputs changed during cache validation"
            )
        return result(manifest, True)
    lock = namespace / ".build.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise IngestError(
            "cache_busy", "Business cache is being built by another process"
        ) from exc
    os.close(fd)
    stage = None
    relative = None
    name = None
    try:
        # A peer may have completed the same generation between lookup and lock.
        if generation.exists():
            manifest = validate_cache(generation, signature, fingerprint)
            if snapshot(business, options) != files:
                raise IngestError(
                    "input_changed", "Business inputs changed during cache validation"
                )
            return result(manifest, True)
        stage = Path(tempfile.mkdtemp(prefix=".building-", dir=namespace))
        database = stage / "raw.duckdb"
        units, source_metadata = [], {}
        with connect(database) as con:
            con.execute(
                "CREATE TABLE __dm_sources(path VARCHAR,sha256 VARCHAR,size_bytes BIGINT,metadata JSON)"
            )
            con.execute("CREATE TABLE __dm_readme(text VARCHAR)")
            try:
                readme_format = inspect_encoding(
                    business / "README.md", error_code="readme_encoding"
                )
                readme = (business / "README.md").read_text(
                    encoding=readme_format["encoding"], errors="strict"
                )
                source_metadata["README.md"] = readme_format
            except IngestError as exc:
                exc.location["source_file"] = "README.md"
                raise
            except UnicodeError as exc:
                raise IngestError(
                    "readme_encoding",
                    "README must be valid UTF-8",
                    source_file="README.md",
                ) from exc
            con.execute("INSERT INTO __dm_readme VALUES (?)", [readme])
            con.execute("""CREATE TABLE __dm_units(source_file VARCHAR,source_name VARCHAR,storage_table VARCHAR,
                        view_name VARCHAR,row_count BIGINT,max_width INTEGER,frame_sha256 VARCHAR,metadata JSON)""")
            used = set()
            for f in files:
                relative = f["path"]
                if relative == "README.md":
                    continue
                override = next(
                    (v for v in options.csv_formats if v.source_file == relative), None
                )
                file_options = (
                    replace(
                        options,
                        csv_encoding=override.encoding,
                        csv_delimiter=override.delimiter,
                    )
                    if override
                    else options
                )
                with closing(read_source(business / relative, file_options)) as readers:
                    for unit in readers:
                        name = unit.name
                        if len(units) >= options.max_units:
                            raise IngestError(
                                "unit_limit", "Business unit limit exceeded"
                            )
                        item = write_unit(con, stage, relative, unit, options)
                        if item["storage_table"] in used:
                            raise IngestError(
                                "unit_collision", "Duplicate source unit identity"
                            )
                        used.add(item["storage_table"])
                        units.append(item)
                        source_metadata[relative] = unit.source_metadata
                        con.execute(
                            "INSERT INTO __dm_units VALUES (?,?,?,?,?,?,?,?)",
                            [
                                relative,
                                name,
                                item["storage_table"],
                                item["view_name"],
                                item["row_count"],
                                item["max_width"],
                                item["frame_sha256"],
                                dump(item["metadata"]),
                            ],
                        )
            for f in files:
                con.execute(
                    "INSERT INTO __dm_sources VALUES (?,?,?,?)",
                    [
                        f["path"],
                        f["sha256"],
                        f["size_bytes"],
                        dump(source_metadata.get(f["path"], {})),
                    ],
                )
        if (
            snapshot(business, options) != files
            or code_hash() != signature["loader_code_sha256"]
        ):
            raise IngestError(
                "input_changed", "Business inputs or loader code changed during build"
            )
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "fingerprint": fingerprint,
            "signature": signature,
            "database_sha256": sha256(database),
            "units": units,
            "source_metadata": source_metadata,
            "model": "not_run",
            "pa": "not_evaluated",
        }
        write_json(stage / "manifest.json", manifest)
        validate_cache(stage, signature, fingerprint)
        stage.rename(generation)
        stage = None
        return result(manifest, False)
    except IngestError as exc:
        exc.location.setdefault("source_file", relative)
        exc.location.setdefault("unit", name)
        raise
    except (ET.ParseError, BadZipFile, KeyError, IndexError, sqlite3.Error) as exc:
        raise IngestError(
            "source_read",
            "Source table stream is malformed or unsupported",
            source_file=relative,
            unit=name,
        ) from exc
    except (OSError, ValueError, UnicodeError, duckdb.Error) as exc:
        raise IngestError(
            "ingest_failed",
            "Business raw ingestion failed",
            source_file=relative,
            unit=name,
        ) from exc
    finally:
        if stage is not None:
            # Only remove the generated, verified staging directory, never raw/cache generations.
            if (
                stage.resolve().parent == namespace.resolve()
                and stage.name.startswith(".building-")
                and not is_link(stage)
            ):
                shutil.rmtree(stage)
        lock.unlink(missing_ok=True)


def ingest_business(
    input_dir: Path,
    business_id: str,
    cache_root: Path,
    options: LoaderOptions | None = None,
) -> dict:
    try:
        return _ingest_business(input_dir, business_id, cache_root, options)
    except IngestError:
        raise
    except (OSError, ValueError, UnicodeError, duckdb.Error) as exc:
        raise IngestError(
            "ingest_failed", "Business input or cache cannot be accessed"
        ) from exc


def ingest_split(
    input_dir: Path,
    cache_root: Path,
    options: LoaderOptions | None = None,
    business_ids: list[str] | None = None,
) -> dict:
    source, cache = roots(Path(input_dir), Path(cache_root))
    data = source / "data"
    if not data.is_dir() or is_link(data):
        raise IngestError(
            "input_path", "Split data/ directory is required and must not be aliased"
        )
    ids = (
        sorted(business_ids)
        if business_ids is not None
        else sorted(p.name for p in data.iterdir())
    )
    if not ids or len(ids) != len(set(ids)):
        raise IngestError(
            "business_id", "Select at least one business, without duplicates"
        )
    if {f.business_id for f in (options or LoaderOptions()).csv_formats} - set(ids):
        raise IngestError(
            "csv_override_unknown",
            "CSV format map references a business outside this run",
        )
    results = []
    for bid in ids:
        try:
            results.append(ingest_business(source, bid, cache, options))
        except IngestError as exc:
            results.append(
                {"valid": False, "business_id": bid, "errors": [exc.record()]}
            )
    return {
        "valid": all(r["valid"] for r in results),
        "scope": "A-T1 raw ingestion; no cleaning/gold/model",
        "input_dir": str(source),
        "cache_root": str(cache),
        "businesses": results,
        "summary": {
            "businesses": len(results),
            "successful": sum(r["valid"] for r in results),
            "cache_hits": sum(r.get("cache_hit", False) for r in results),
            "units": sum(len(r.get("units", [])) for r in results),
            "rows": sum(r.get("rows", 0) for r in results),
            "nonempty_rows": sum(r.get("nonempty_rows", 0) for r in results),
        },
        "gold_content_read": False,
        "model": "not_run",
        "pa": "not_evaluated",
    }


def run_ingest(
    input_dir: Path,
    cache_root: Path,
    output_dir: Path,
    options: LoaderOptions | None = None,
    business_ids: list[str] | None = None,
    format_map: Path | None = None,
) -> dict:
    source, cache = roots(Path(input_dir), Path(cache_root))
    output = output_dir.resolve()
    if not disjoint(output, source) or not disjoint(output, cache) or output.exists():
        raise IngestError(
            "output_overlap", "Report output must be new and disjoint from input/cache"
        )
    map_hash = None
    if format_map is not None:
        mapping = Path(format_map).resolve(strict=True)
        if (
            not disjoint(mapping, source)
            or not disjoint(mapping, cache)
            or not disjoint(mapping, output)
            or mapping.stat().st_size > 8 * 1024 * 1024
        ):
            raise IngestError(
                "csv_override_map",
                "Format map must be bounded and outside source/cache/output",
            )
        try:
            obj = json.loads(mapping.read_text("utf-8"))
            if (
                set(obj) != {"version", "files"}
                or type(obj["version"]) is not int
                or obj["version"] != 1
            ):
                raise ValueError
            options = replace(
                options or LoaderOptions(),
                csv_formats=tuple(CsvFormat(**v) for v in obj["files"]),
            )
            map_hash = sha256(mapping)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise IngestError(
                "csv_override_map", "Invalid source-bound format map"
            ) from exc
    result = ingest_split(source, cache, options, business_ids)
    if format_map is not None and sha256(mapping) != map_hash:
        raise IngestError("input_changed", "CSV format map changed during ingestion")
    result["format_map_sha256"] = map_hash
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "ingest.json", result)
    return result
