from dataclasses import asdict, dataclass

from datamate.ingest import IngestError


@dataclass(frozen=True)
class ProfileOptions:
    detect_headers: bool = True
    header_scan_rows: int = 64
    header_scan_bytes: int = 1024 * 1024
    data_sample_rows: int = 128
    samples_per_column: int = 3
    preview_rows: int = 6
    preview_columns: int = 32
    value_bytes: int = 256
    max_columns: int = 16384
    max_units: int = 1024
    max_rows_per_unit: int = 5_000_000
    max_cells_per_business: int = 100_000_000
    max_retained_bytes_per_unit: int = 16 * 1024 * 1024
    max_report_bytes_per_business: int = 64 * 1024 * 1024
    max_numeric_chars: int = 128

    def __post_init__(self):
        if type(self.detect_headers) is not bool or any(
            type(v) is not int or v < 1
            for k, v in asdict(self).items()
            if k != "detect_headers"
        ):
            raise IngestError(
                "profile_config", "Profile limits must be positive integers"
            )
        if (
            self.samples_per_column > 10
            or self.preview_rows > 64
            or self.preview_columns > 256
            or not 4 <= self.value_bytes <= 8192
            or self.max_columns > 16384
            or self.max_numeric_chars > 4096
            or self.header_scan_rows > 256
            or self.data_sample_rows > 1024
        ):
            raise IngestError(
                "profile_config",
                "Profile preview/numeric limits exceed supported bounds",
            )
