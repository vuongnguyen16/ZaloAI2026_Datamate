import codecs
from dataclasses import asdict, dataclass, field
from typing import Iterator


class IngestError(ValueError):
    """Stable diagnostic with no source cell value in its message."""

    def __init__(self, code: str, message: str, **location):
        super().__init__(message)
        self.code = code
        self.location = {k: v for k, v in location.items() if v is not None}

    def record(self) -> dict:
        return {"code": self.code, "message": str(self), **self.location}


@dataclass(frozen=True)
class LoaderOptions:
    csv_encoding: str = "utf-8-sig"
    csv_delimiter: str = ","
    max_source_bytes: int = 1024 * 1024 * 1024
    max_business_bytes: int = 2 * 1024 * 1024 * 1024
    max_units: int = 1024
    max_xml_bytes: int = 256 * 1024 * 1024
    max_zip_bytes: int = 1024 * 1024 * 1024
    max_metadata_bytes: int = 8 * 1024 * 1024
    max_shared_strings_bytes: int = 64 * 1024 * 1024
    max_cell_bytes: int = 1024 * 1024
    max_row_bytes: int = 8 * 1024 * 1024
    max_staging_bytes: int = 1024 * 1024 * 1024
    max_columns: int = 16384
    max_rows: int = 5_000_000
    sqlite_timeout_seconds: float = 60.0

    def __post_init__(self):
        try:
            codecs.lookup(self.csv_encoding)
        except LookupError as exc:
            raise IngestError("config", "Unknown CSV encoding") from exc
        if len(self.csv_delimiter) != 1 or self.csv_delimiter in '\r\n"\0':
            raise IngestError("config", "CSV delimiter must be one supported character")
        for key, value in asdict(self).items():
            if key.startswith("max_") and (type(value) is not int or value < 1):
                raise IngestError("config", "Resource limits must be positive integers")
        if not 1 <= self.max_columns <= 16384:
            raise IngestError("config", "Column limit must be between 1 and 16384")
        if not 0 < self.sqlite_timeout_seconds <= 3600:
            raise IngestError("config", "SQLite deadline must be in (0, 3600]")


@dataclass
class RawRow:
    number: int
    width: int
    values: dict[int, str | None]
    metadata: dict = field(default_factory=dict)


@dataclass
class RawUnit:
    name: str
    kind: str
    rows: Iterator[RawRow]
    metadata: dict = field(default_factory=dict)
    source_metadata: dict = field(default_factory=dict)
