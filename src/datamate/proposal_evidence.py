"""Source-located excerpts; never substitute a prefix for missing evidence."""

import hashlib
import re
from pathlib import PurePosixPath


def _spans(text, intervals, source, source_sha256=None):
    lines = text.splitlines(keepends=True)
    digest = source_sha256 or hashlib.sha256(text.encode()).hexdigest()
    result = []
    for first, last in sorted(set(intervals)):
        result.append(
            dict(
                source=source,
                sha256=digest,
                hash_scope="raw_file_bytes" if source_sha256 else "decoded_text_utf8",
                line_start=first + 1,
                line_end=last,
                text="".join(lines[first:last]).rstrip("\r\n"),
            )
        )
    return result


def project_rulebook(text, kind="status", source_sha256=None):
    lines = text.splitlines(keepends=True)
    markers = (
        "| Trạng thái đơn |",
        "| Đơn tính vào doanh thu |",
        "| Đơn bị huỷ |",
        "| Số đơn |",
    )
    if kind == "source":
        markers += ("| Doanh thu một đơn |", "| Tên gọi, nhãn |", "| Ô để trống")
    intervals = []
    for i, line in enumerate(lines):
        if (
            any(m.casefold() in line.casefold() for m in markers)
            or "Riêng trạng thái huỷ" in line
        ):
            intervals.append((i, i + 1))
    spans = _spans(text, intervals, "rulebook.md", source_sha256)
    has_status = any("| trạng thái đơn |" in s["text"].casefold() for s in spans)
    return spans, dict(
        omitted=len(intervals) < len(lines),
        required_evidence_missing=not has_status,
        selection="status_and_metric_clauses",
        source_lines=len(lines),
        retained_lines=len(intervals),
    )


def project_readme(
    text, source_file, source_name, source_sha256=None, *, database_files=()
):
    lines = text.splitlines(keepends=True)

    def section(file):
        intervals = []
        for i, line in enumerate(lines):
            if re.fullmatch(
                r"#{2,3}\s+Cột trong `" + re.escape(file) + r"`\s*",
                line.strip(),
                re.IGNORECASE,
            ):
                end = next(
                    (
                        j
                        for j in range(i + 1, len(lines))
                        if re.match(r"^#{1,3}\s", lines[j])
                    ),
                    len(lines),
                )
                intervals.append((i, end))
        return intervals

    intervals = section(source_file)
    match = "exact" if intervals else "unmatched"
    if not intervals:
        declaration = [
            i
            for i, line in enumerate(lines)
            if "tách thành nhiều file" in line.casefold()
        ]
        base = re.sub(r"_\d+(?=\.[^.]+$)", "", source_file)
        if declaration and base != source_file and section(base):
            intervals = section(base) + [(i, i + 1) for i in declaration]
            match = "declared_partition"
    if not intervals and PurePosixPath(source_file).suffix.casefold() in {
        ".sqlite",
        ".db",
        ".sqlite3",
    }:
        pattern = r"`" + re.escape(source_name) + r"(?:[.`])"
        headings = [
            (i, len(re.match(r"^(#+)", line)[1]))
            for i, line in enumerate(lines)
            if re.match(r"^#{1,3}\s", line)
        ]
        scoped = set()
        for first, level in headings:
            if re.search(
                r"(?<![\w.])" + re.escape(source_file) + r"(?![\w.])", lines[first]
            ):
                last = next(
                    (i for i, depth in headings if i > first and depth <= level),
                    len(lines),
                )
                scoped.update(range(first + 1, last))
        mentioned = set(
            re.findall(r"[\w.-]+\.(?:sqlite3|sqlite|db)\b", text, re.IGNORECASE)
        )
        singleton = set(database_files) == {source_file} and mentioned <= {source_file}
        intervals = [
            (i, i + 1)
            for i, line in enumerate(lines)
            if re.search(pattern, line) and (i in scoped or singleton)
        ]
        if intervals:
            match = "file_table_reference" if scoped else "table_reference"
    spans = _spans(text, intervals, "README.md", source_sha256)
    retained = {i for first, last in intervals for i in range(first, last)}
    return spans, dict(
        match=match,
        omitted=len(retained) < len(lines),
        required_evidence_missing=not bool(spans),
        source_lines=len(lines),
        retained_lines=len(retained),
    )


def project_business_readme(business, unit):
    """Use the verified raw digest and known DB inventory, never a guessed filename."""
    digest = next(
        r["sha256"]
        for r in business.profile["provenance"]["files"]
        if r["path"] == "README.md"
    )
    databases = {
        u["source_file"]
        for u in business.schema["tables"]
        if PurePosixPath(u["source_file"]).suffix.casefold()
        in {".sqlite", ".sqlite3", ".db"}
    }
    return project_readme(
        business.readme,
        unit["source_file"],
        unit["source_name"],
        digest,
        database_files=databases,
    )


def combine_spans(spans, metadata):
    evidence = ""
    locators = []
    for span in spans:
        if evidence:
            evidence += "\n\n---\n\n"
        start = len(evidence)
        evidence += span["text"]
        locators.append(
            {k: v for k, v in span.items() if k != "text"}
            | dict(start=start, end=len(evidence))
        )
    return evidence, dict(
        version=2,
        spans=locators,
        omitted=any(m.get("omitted") for m in metadata),
        required_evidence_missing=any(
            m.get("required_evidence_missing") for m in metadata
        ),
        selection=metadata,
    )
