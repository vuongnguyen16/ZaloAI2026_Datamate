"""Deterministic strict byte/CSV policy; no 8-bit guessing or text repair."""

import codecs
import csv
from collections import Counter

from datamate.ingest.model import IngestError


def inspect_encoding(path, configured="auto", *, error_code="csv_encoding"):
    with path.open("rb") as h:
        prefix = h.read(4)
    if prefix.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        raise IngestError(
            error_code,
            "UTF-32 BOM is unsupported by the runtime policy",
            encoding_status="unsupported_bom",
        )
    bom = (
        "utf-8"
        if prefix.startswith(codecs.BOM_UTF8)
        else "utf-16-le"
        if prefix.startswith(codecs.BOM_UTF16_LE)
        else "utf-16-be"
        if prefix.startswith(codecs.BOM_UTF16_BE)
        else None
    )
    codec = "utf-8-sig" if bom == "utf-8" else "utf-16" if bom else "utf-8"
    if configured != "auto":
        normalized = codecs.lookup(configured).name
        compatible = (
            {"utf-8", "utf-8-sig"}
            if bom == "utf-8"
            else {"utf-16", bom}
            if bom
            else {normalized}
        )
        if normalized not in compatible:
            raise IngestError(
                error_code,
                "Configured encoding conflicts with source BOM",
                encoding_status="bom_conflict",
            )
        if not bom:
            codec = configured
    decoder = codecs.getincrementaldecoder(codec)(errors="strict")
    ascii_only, size = True, 0
    try:
        with path.open("rb") as h:
            while chunk := h.read(65536):
                size += len(chunk)
                ascii_only &= chunk.isascii()
                decoder.decode(chunk, final=False)
            decoder.decode(b"", final=True)
    except UnicodeError as exc:
        raise IngestError(
            error_code,
            "Source cannot be strictly decoded by runtime policy",
            encoding_status="undecodable",
        ) from exc
    status = (
        "configured_override"
        if configured != "auto"
        else "bom_" + bom.replace("-", "_")
        if bom
        else "empty"
        if not size
        else "ascii_only"
        if ascii_only
        else "utf8_validated"
    )
    return {
        "encoding": codec,
        "encoding_status": status,
        "bom": bom,
        "format_policy_version": 1,
    }


def inspect_csv(path, options):
    metadata = inspect_encoding(path, options.csv_encoding)
    if options.csv_delimiter != "auto":
        return {
            **metadata,
            "delimiter": options.csv_delimiter,
            "delimiter_status": "configured",
        }
    candidates = []
    previous = csv.field_size_limit()
    csv.field_size_limit(options.max_cell_bytes)
    try:
        for delimiter in (",", ";", "\t", "|"):
            widths = []
            try:
                with path.open(encoding=metadata["encoding"], newline="") as h:
                    for number, row in enumerate(
                        csv.reader(h, delimiter=delimiter, strict=True), 1
                    ):
                        if row:
                            widths.append(len(row))
                        if number >= 64:
                            break
            except csv.Error:
                continue
            multi = sum(w > 1 for w in widths)
            if multi and multi * 2 >= len(widths):
                candidates.append(
                    {
                        "delimiter": delimiter,
                        "sample_records": len(widths),
                        "multicolumn_records": multi,
                        "widths": dict(sorted(Counter(widths).items())),
                        "stable_width": len(set(widths)) == 1,
                    }
                )
        stable = [c for c in candidates if c["stable_width"]]
        if stable:
            candidates = stable
        if len(candidates) > 1:
            raise IngestError(
                "csv_delimiter_ambiguous",
                "CSV delimiter candidates conflict; supply a source-bound override",
            )
        if candidates:
            return {
                **metadata,
                "delimiter": candidates[0]["delimiter"],
                "delimiter_status": "auto_unique",
                "delimiter_evidence": candidates[0],
            }
        # Single-column/empty files are valid; strict parsing still runs in the reader.
        return {
            **metadata,
            "delimiter": ",",
            "delimiter_status": "single_column_default",
        }
    finally:
        csv.field_size_limit(previous)
