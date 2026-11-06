import codecs
import re
from dataclasses import asdict, dataclass, field
from pathlib import PurePosixPath
from typing import Iterator


class IngestError(ValueError):
    """Mẫu phiếu báo lỗi chung khi nạp dữ liệu.

    Để mọi chỗ trong chương trình báo lỗi theo cùng một cách, luôn đủ
    3 thông tin:
    * 1. Lỗi gì? (``code``)
    * 2. Thế nào? (``message``)
    * 3. Ở đâu? (``location``)
    
    Quy định: trên phiếu không được chép nội dung dữ liệu gốc
    (giá trị trong ô), để bảo mật dữ liệu.
    
    Cách dùng:
        Báo lỗi (ném phiếu lên)::

            raise IngestError("row_limit", "Too many rows", source_file="sales.csv")

        Bắt lỗi và ghi ra JSON::

            try:
                ...
            except IngestError as exc:
                errors.append(exc.record())
    """

    def __init__(self, code: str, message: str, **location):
        """Tạo một phiếu báo lỗi.

        Args:
            code: Lỗi gì, ví dụ ``"row_limit"``.
            message: Mô tả lỗi cho người đọc.
            **location: Lỗi ở đâu, truyền dạng tên=giá trị, ví dụ
                ``source_file="sales.csv", unit="sales"``.
                Giá trị ``None`` bị bỏ qua.
        """
        # Giao message cho ValueError giữ, để str(lỗi) in ra đúng câu này.
        super().__init__(message)
        self.code = code
        self.location = {k: v for k, v in location.items() if v is not None}

    def record(self) -> dict:
        """Đổi phiếu báo lỗi thành dict để ghi ra JSON.

        Returns:
            dict: Gồm ``code``, ``message`` và các mục trong ``location``.
        """
        return {"code": self.code, "message": str(self), **self.location}


@dataclass(frozen=True)      
class CsvFormat:
    """
    CsvFormat là tờ ghi chú cách đọc riêng cho đúng một file CSV, 
    gồm: file nào (business, đường dẫn, mã niêm phong) và đọc thế nào (bảng mã, ký tự ngăn cách). 
    Mã niêm phong đảm bảo ghi chú chỉ áp dụng khi file chưa bị thay đổi.       
    """
    business_id: str
    source_file: str
    source_sha256: str
    encoding: str = "auto"          # Mặc định tự đoán (có thể sai)
    delimiter: str = "auto"         # Mặc định tự đoán (có thể sai)
    
    def __post_init__(self):
        """Kiểm tra tính hợp lệ của các thuộc tính. Nếu không hợp lệ, ném IngestError."""
        if (
            not self.business_id
            or any(c in self.business_id for c in "/\\:\0")
            or not isinstance(self.source_file, str)
            or "\\" in self.source_file
            or PurePosixPath(self.source_file).is_absolute()
            or any(p in {".", ".."} for p in self.source_file.split("/"))
            or not self.source_file.lower().endswith(".csv")
            or not re.fullmatch(r"[0-9a-f]{64}", self.source_sha256)
        ):
            raise IngestError("config", "Invalid source-bound CSV format override")
        validate_format(self.encoding, self.delimiter)


def validate_format(encoding, delimiter):
    try:
        if encoding != "auto":
            codecs.lookup(encoding)
    except (LookupError, TypeError) as exc:
        raise IngestError("config", "Unknown CSV encoding") from exc
    if not isinstance(delimiter, str) or (
        delimiter != "auto" and (len(delimiter) != 1 or delimiter in '\r\n"\0')
    ):
        raise IngestError(
            "config", "CSV delimiter must be auto or one supported character"
        )


@dataclass(frozen=True)
class LoaderOptions:
    csv_encoding: str = "auto"
    csv_delimiter: str = "auto"
    csv_formats: tuple[CsvFormat, ...] = ()
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
        validate_format(self.csv_encoding, self.csv_delimiter)
        formats = tuple(
            f if isinstance(f, CsvFormat) else CsvFormat(**f) for f in self.csv_formats
        )
        if len({(f.business_id, f.source_file) for f in formats}) != len(formats):
            raise IngestError("config", "Duplicate source-bound CSV format override")
        object.__setattr__(self, "csv_formats", formats)
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
