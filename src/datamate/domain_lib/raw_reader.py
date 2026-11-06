"""Read verified A-T1/A-T2 business artifacts without changing raw inputs."""

import hashlib
import json
import platform
import re
from contextlib import contextmanager
from pathlib import Path

import duckdb

from datamate.ingest import loader
from datamate.ingest.text_format import inspect_encoding
from datamate.model_probe import safe_relative
from datamate.prediction_store import regular_bytes, safe_path
from datamate.profile.engine import code_hash, schema_descriptor

from .model import DomainAbstain
from .orders import RawRow


def file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _json(path, limit=64 * 1024**2):
    path = safe_path(Path(path))
    raw = regular_bytes(path, limit, single_link=True)
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def _verify_unit_inventory(profile, schema, units):
    expected = {u["view_name"]: u for u in units}
    observed = {u["view_name"]: u for u in profile["units"]}
    if (
        len(expected) != len(units)
        or len(observed) != len(profile["units"])
        or set(expected) != set(observed)
        or {u["sql_name"] for u in schema["tables"]} != set(expected)
    ):
        raise DomainAbstain("incomplete_profile_inventory")
    fields = (
        "source_file",
        "source_name",
        "source_kind",
        "storage_table",
        "view_name",
        "row_count",
        "max_width",
        "frame_sha256",
    )
    for name, unit in expected.items():
        actual = observed[name]
        if any(actual.get(k) != unit.get(k) for k in fields) or [
            c["sql_name"] for c in actual["columns"]
        ] != [f"c{i:04d}" for i in range(1, unit["max_width"] + 1)]:
            raise DomainAbstain("incomplete_profile_columns")
        declared = unit.get("metadata", {}).get("columns", [])
        for i, column in enumerate(actual["columns"]):
            if unit["source_kind"] == "sqlite_table":
                if (
                    i >= len(declared)
                    or column.get("declared_name") != declared[i][1]
                    or column.get("declared_type") != declared[i][2]
                ):
                    raise DomainAbstain("declared_column_mismatch")
            elif "declared_name" in column or "declared_type" in column:
                raise DomainAbstain("unexpected_declared_column")


def _verify_headers(con, profile):
    for unit in profile["units"]:
        coords = {
            h["source_row"] for c in unit["columns"] for h in c.get("header_cells", [])
        }
        structure = unit["header"]
        header_rows = structure["rows"]
        if len(header_rows) != len(set(header_rows)) or set(header_rows) != coords:
            raise DomainAbstain("header_coordinate_mismatch")
        status = structure["status"]
        if status == "source_schema":
            if (
                unit["source_kind"] != "sqlite_table"
                or coords
                or structure["data_start_row"] != (1 if unit["row_count"] else None)
            ):
                raise DomainAbstain("unverified_data_boundary")
        elif status in {"auto_rule", "explicit_annotation"}:
            if not coords or any(type(n) is not int or n < 1 for n in coords):
                raise DomainAbstain("invalid_header_coordinate")
            nonempty = " OR ".join(
                f"({loader.identifier(c['sql_name'])} IS NOT NULL AND {loader.identifier(c['sql_name'])}<>'')"
                for c in unit["columns"]
            )
            first_data = con.execute(
                f"SELECT min(__row) FROM {loader.identifier(unit['view_name'])} WHERE __row>? AND ({nonempty})",
                [max(coords)],
            ).fetchone()[0]
            if structure["data_start_row"] != first_data:
                raise DomainAbstain("unverified_data_boundary")
        if not coords:
            continue
        if any(type(n) is not int or not 1 <= n <= unit["row_count"] for n in coords):
            raise DomainAbstain("invalid_header_coordinate")
        columns = [c["sql_name"] for c in unit["columns"]]
        query = f"SELECT __row,{','.join(loader.identifier(c) for c in columns)} FROM {loader.identifier(unit['view_name'])} WHERE __row IN ({','.join('?' for _ in coords)})"
        actual = {
            r[0]: dict(zip(columns, r[1:], strict=True))
            for r in con.execute(query, sorted(coords)).fetchall()
        }
        for column in unit["columns"]:
            for record in column.get("header_cells", []):
                value = record.get("cell")
                if isinstance(value, dict):
                    if value.get("truncated") is True:
                        continue
                    value = value.get("value")
                if (
                    actual.get(record["source_row"], {}).get(column["sql_name"])
                    != value
                ):
                    raise DomainAbstain("header_evidence_mismatch")


class VerifiedBusiness:
    def __init__(self, con, schema, profile, readme, proof):
        self._con = con
        self._schema = json.loads(json.dumps(schema))
        self.profile = profile
        self.readme = readme
        self.proof = proof
        self._units = {t["sql_name"]: t for t in self._schema["tables"]}
        self._consumed = {}
        self.closed = False

    @property
    def schema(self):
        return json.loads(json.dumps(self._schema))

    @property
    def consumed(self):
        return dict(self._consumed)

    def iter_rows(self, unit):
        name = unit.get("sql_name")
        if (
            self.closed
            or self._units.get(name) != unit
            or not re.fullmatch(r"raw_[0-9a-f]{24}", name or "")
        ):
            raise DomainAbstain("unverified_unit")
        columns = [c["sql_name"] for c in unit["columns"]]
        if any(not re.fullmatch(r"c\d{4,5}", c) for c in columns):
            raise DomainAbstain("unverified_column")
        cursor = self._con.cursor()
        count = previous = 0
        try:
            select = ",".join(loader.identifier(c) for c in ["__row", *columns])
            cursor.execute(
                f"SELECT {select} FROM {loader.identifier(name)} ORDER BY __row"
            )
            while chunk := cursor.fetchmany(1024):
                for record in chunk:
                    number = record[0]
                    if type(number) is not int or number <= previous:
                        raise DomainAbstain("raw_coordinate_conflict")
                    previous = number
                    count += 1
                    yield RawRow(number, dict(zip(columns, record[1:], strict=True)))
            if count != unit["row_count"]:
                raise DomainAbstain("raw_row_count_changed")
            self._consumed[name] = count
        finally:
            cursor.close()


@contextmanager
def open_business(index: Path, source: Path, business_id: str):
    """Scope authorization belongs to the caller; no questions/gold are opened."""
    con = None
    business = None
    try:
        source = safe_path(Path(source))
        index = safe_path(Path(index))
        if not loader.disjoint(source, index):
            raise DomainAbstain("profile_overlaps_raw")
        raw = loader.business_path(source, business_id)
        idx, index_sha = _json(index, 8 * 1024**2)
        if (
            idx.get("valid") is not True
            or idx.get("gold_content_read") is not False
            or idx.get("profile_code_sha256") != code_hash()
        ):
            raise DomainAbstain("unverified_profile_index")
        selected = [b for b in idx["businesses"] if b["business_id"] == business_id]
        if len(selected) != 1 or selected[0].get("valid") is not True:
            raise DomainAbstain("unverified_business")
        entry = selected[0]
        loaded = {}
        tracked = {index: index_sha}
        for kind in ["profile", "schema"]:
            path = safe_path(Path(entry[kind]["path"]))
            if index.parent not in path.parents or not loader.disjoint(source, path):
                raise DomainAbstain("unverified_artifact_path")
            value, sha = _json(path)
            if sha != entry[kind]["sha256"]:
                raise DomainAbstain("profile_hash_changed")
            loaded[kind] = value
            tracked[path] = sha
        profile, schema = loaded["profile"], loaded["schema"]
        if profile["business_id"] != business_id or schema != schema_descriptor(
            profile
        ):
            raise DomainAbstain("schema_profile_mismatch")
        provenance = profile["provenance"]
        database = safe_path(Path(provenance["database"]))
        if database.name != "raw.duckdb" or not loader.disjoint(source, database):
            raise DomainAbstain("invalid_cache_path")
        manifest_path = database.with_name("manifest.json")
        manifest, manifest_sha = _json(manifest_path)
        fingerprint = provenance["ingest_fingerprint"]
        signature = manifest["signature"]
        if (
            manifest_sha != provenance["manifest_sha256"]
            or signature["business_id"] != business_id
            or signature["files"] != provenance["files"]
            or signature["loader_code_sha256"] != loader.code_hash()
            or signature["duckdb_version"] != duckdb.__version__
            or signature["python_version"] != platform.python_version()
            or hashlib.sha256(loader.dump(signature).encode()).hexdigest()
            != fingerprint
        ):
            raise DomainAbstain("stale_ingest_identity")
        checked = loader.validate_cache(database.parent, signature, fingerprint)
        _verify_unit_inventory(profile, schema, checked["units"])
        if checked["database_sha256"] != provenance["database_sha256"]:
            raise DomainAbstain("cache_profile_mismatch")
        tracked[database] = provenance["database_sha256"]
        tracked[manifest_path] = manifest_sha
        options = loader.LoaderOptions(**signature["options"])
        if loader.snapshot(raw, options) != provenance["files"]:
            raise DomainAbstain("source_changed")
        source_files = {}
        for record in provenance["files"]:
            if not safe_relative(record["path"]):
                raise DomainAbstain("unsafe_source_path")
            path = safe_path(raw / record["path"])
            if not path.is_relative_to(raw) or file_hash(path) != record["sha256"]:
                raise DomainAbstain("source_changed")
            source_files[path] = record["sha256"]
        readme = raw / "README.md"
        if readme not in source_files:
            raise DomainAbstain("readme_not_verified")
        text = readme.read_text(inspect_encoding(readme)["encoding"])
        con = loader.connect(database, read_only=True)
        _verify_headers(con, profile)
        business = VerifiedBusiness(
            con,
            schema,
            profile,
            text,
            dict(
                index_sha256=index_sha,
                database_sha256=provenance["database_sha256"],
                manifest_sha256=manifest_sha,
                schema_sha256=entry["schema"]["sha256"],
                profile_sha256=entry["profile"]["sha256"],
            ),
        )
        try:
            yield business
        finally:
            business.closed = True
            if loader.snapshot(raw, options) != provenance["files"]:
                raise DomainAbstain("source_changed")
            for path, sha in source_files.items():
                if file_hash(path) != sha:
                    raise DomainAbstain("source_changed")
            for path, sha in tracked.items():
                if file_hash(path) != sha:
                    raise DomainAbstain("artifact_changed")
    except (ValueError, KeyError, TypeError, OSError, duckdb.Error) as exc:
        if isinstance(exc, DomainAbstain):
            raise
        raise DomainAbstain("unverified_business_artifact") from None
    finally:
        if business is not None:
            business.closed = True
        if con is not None:
            con.close()
