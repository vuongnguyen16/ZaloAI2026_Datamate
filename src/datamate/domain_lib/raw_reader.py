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
        if checked["database_sha256"] != provenance["database_sha256"]:
            raise DomainAbstain("cache_profile_mismatch")
        tracked[database] = provenance["database_sha256"]
        tracked[manifest_path] = manifest_sha
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
