"""Mechanical data inventory by business, supporting timeline group A.

Audits dataset structure, file sizes, SHA-256 hashes, question references
and identical table files across businesses without analyzing question text,
evaluating data values, or parsing gold answers. All files are hashed as bytes.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from datamate.artifacts import sha256 as get_sha256
except ImportError:
    import hashlib

    def get_sha256(path: Path) -> str:
        with path.open("rb") as handle:
            return hashlib.file_digest(handle, "sha256").hexdigest()


TABLE_EXTENSIONS = {".csv", ".xlsx", ".sqlite"}


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            # Do not echo arbitrary keys from question content into reports.
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("non-standard JSON constant")


def _format_bytes(byte_count: int) -> str:
    """Format byte count into human-readable representation."""
    if byte_count < 1024:
        return f"{byte_count} B"
    elif byte_count < 1024 * 1024:
        return f"{byte_count:,} B ({byte_count / 1024:.2f} KiB)"
    else:
        return f"{byte_count:,} B ({byte_count / (1024 * 1024):.2f} MiB)"


def build_inventory(input_dir: Path) -> dict[str, Any]:
    """Scan and build structural inventory from input split directory.

    Strict contract rules:
    - Never opens or parses answers.jsonl as JSON/gold.
    - Does not store or output question text.
    - Does not inspect cell/table data content or schema.
    - Uses streaming binary SHA-256 for all files.
    """
    directory = input_dir.resolve()
    if not directory.is_dir():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    errors: list[dict[str, Any]] = []

    # 1. Discover business directories under data/
    data_dir = directory / "data"
    business_dirs: set[str] = set()
    if not data_dir.is_dir():
        errors.append(
            {
                "type": "missing_data_dir",
                "path": "data",
                "message": f"Business data directory not found: {data_dir.name}",
            }
        )
    else:
        for entry in data_dir.iterdir():
            if entry.is_dir():
                if entry.name in (".", "..") or any(
                    c in entry.name for c in ("/", "\\", ":")
                ):
                    errors.append(
                        {
                            "type": "invalid_business_directory_name",
                            "business_id": entry.name,
                            "message": f"Invalid business directory name: {entry.name}",
                        }
                    )
                else:
                    business_dirs.add(entry.name)

    # 2. Enumerate all files in input directory (streaming hash, size)
    all_files: dict[str, dict[str, Any]] = {}
    table_hashes: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        rel_posix = path.relative_to(directory).as_posix()
        size_bytes = path.stat().st_size
        file_hash = get_sha256(path)
        record = {
            "path": rel_posix,
            "size_bytes": size_bytes,
            "sha256": file_hash,
        }
        all_files[rel_posix] = record

        # Check table files
        ext = path.suffix.lower()
        if ext in TABLE_EXTENSIONS:
            biz_id: str | None = None
            parts = rel_posix.split("/")
            if len(parts) >= 3 and parts[0] == "data" and parts[1] in business_dirs:
                biz_id = parts[1]
            table_hashes[file_hash].append(
                {
                    "path": rel_posix,
                    "business_id": biz_id,
                    "size_bytes": size_bytes,
                }
            )

    # 3. Group identical table files
    identical_table_files: list[dict[str, Any]] = []
    for h, group in sorted(table_hashes.items()):
        if len(group) > 1:
            biz_set = sorted(
                list({item["business_id"] for item in group if item["business_id"]})
            )
            paths = sorted([item["path"] for item in group])
            identical_table_files.append(
                {
                    "sha256": h,
                    "size_bytes": group[0]["size_bytes"],
                    "file_count": len(group),
                    "files": paths,
                    "businesses": biz_set,
                    "observation_note": (
                        "Các file bảng có cùng SHA-256; chỉ ghi nhận quan sát trùng khớp byte, "
                        "không tự kết luận các doanh nghiệp trùng nhau."
                    ),
                }
            )

    # 4. Scan questions.jsonl (line-by-line mechanical parsing)
    questions_file = directory / "questions.jsonl"
    questions_per_business: Counter[str] = Counter()
    seen_question_ids: dict[str, int] = {}
    candidate_business_by_id: dict[str, str] = {}
    duplicate_question_ids: set[str] = set()
    question_lines = 0

    if not questions_file.is_file():
        errors.append(
            {
                "type": "missing_file",
                "path": "questions.jsonl",
                "message": "Required file questions.jsonl not found",
            }
        )
    else:
        with questions_file.open(encoding="utf-8-sig") as handle:
            for line_number, raw_line in enumerate(handle, 1):
                question_lines += 1
                line = raw_line.strip()
                if not line:
                    errors.append(
                        {
                            "type": "malformed_jsonl",
                            "line": line_number,
                            "message": f"Blank line {line_number} in questions.jsonl",
                        }
                    )
                    continue

                try:
                    item = json.loads(
                        line,
                        object_pairs_hook=_unique_keys,
                        parse_constant=_reject_constant,
                    )
                except (ValueError, RecursionError):
                    errors.append(
                        {
                            "type": "malformed_jsonl",
                            "line": line_number,
                            "message": f"Invalid JSON on line {line_number}",
                        }
                    )
                    continue

                if not isinstance(item, dict):
                    errors.append(
                        {
                            "type": "not_an_object",
                            "line": line_number,
                            "message": f"JSON record on line {line_number} is not an object",
                        }
                    )
                    continue

                # Check question id
                qid = item.get("id")
                qid_valid = False
                if qid is None or not isinstance(qid, str) or not qid.strip():
                    errors.append(
                        {
                            "type": "missing_id",
                            "line": line_number,
                            "message": f"Line {line_number}: missing or empty 'id' field",
                        }
                    )
                else:
                    if qid in seen_question_ids:
                        duplicate_question_ids.add(qid)
                        errors.append(
                            {
                                "type": "duplicate_question_id",
                                "question_id": qid,
                                "line": line_number,
                                "first_seen_line": seen_question_ids[qid],
                                "message": (
                                    f"Duplicate question ID '{qid}' on line {line_number} "
                                    f"(first seen on line {seen_question_ids[qid]})"
                                ),
                            }
                        )
                    else:
                        seen_question_ids[qid] = line_number
                        qid_valid = True

                # Check business_id
                bid = item.get("business_id")
                if bid is None or not isinstance(bid, str) or not bid.strip():
                    errors.append(
                        {
                            "type": "missing_business_id",
                            "line": line_number,
                            "question_id": qid if qid_valid else None,
                            "message": f"Line {line_number}: missing or empty 'business_id' field",
                        }
                    )
                else:
                    if bid in (".", "..") or any(c in bid for c in ("/", "\\", ":")):
                        errors.append(
                            {
                                "type": "invalid_business_reference",
                                "line": line_number,
                                "question_id": qid if qid_valid else None,
                                "business_id": bid,
                                "message": (
                                    f"Invalid business reference characters '{bid}' "
                                    f"on line {line_number}"
                                ),
                            }
                        )
                    else:
                        if bid not in business_dirs:
                            errors.append(
                                {
                                    "type": "nonexistent_business",
                                    "line": line_number,
                                    "question_id": qid if qid_valid else None,
                                    "business_id": bid,
                                    "message": f"Line {line_number}: business directory not found",
                                }
                            )
                        elif qid_valid:
                            candidate_business_by_id[qid] = bid

    # Exclude every occurrence of a duplicated ID, including the first one.
    # This avoids assigning ambiguous questions according to input order.
    questions_per_business.update(
        bid
        for qid, bid in candidate_business_by_id.items()
        if qid not in duplicate_question_ids
    )

    # 5. Build per-business statistics
    businesses_list: list[dict[str, Any]] = []
    for biz_id in sorted(business_dirs):
        prefix = f"data/{biz_id}/"
        biz_files = [
            f for path_k, f in sorted(all_files.items()) if path_k.startswith(prefix)
        ]
        ext_counter = Counter(Path(f["path"]).suffix.lower() for f in biz_files)
        total_biz_bytes = sum(f["size_bytes"] for f in biz_files)
        businesses_list.append(
            {
                "business_id": biz_id,
                "question_count": questions_per_business.get(biz_id, 0),
                "file_count": len(biz_files),
                "total_bytes": total_biz_bytes,
                "extension_distribution": dict(sorted(ext_counter.items())),
                "files": [
                    {
                        "path": f["path"],
                        "size_bytes": f["size_bytes"],
                        "sha256": f["sha256"],
                    }
                    for f in biz_files
                ],
            }
        )

    # 6. Overall summary
    total_files = len(all_files)
    total_bytes = sum(f["size_bytes"] for f in all_files.values())
    biz_files_count = sum(b["file_count"] for b in businesses_list)
    biz_bytes_count = sum(b["total_bytes"] for b in businesses_list)
    top_level_files = total_files - biz_files_count
    top_level_bytes = total_bytes - biz_bytes_count

    errors_sorted = sorted(
        errors,
        key=lambda e: (
            e.get("line") or 0,
            e.get("type", ""),
            e.get("message", ""),
        ),
    )

    return {
        "scope": "p01_data_inventory_structural_only",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_dir": str(directory),
        "question_count_policy": (
            "total_questions and per-business question_count count nonempty string IDs "
            "occurring exactly once in parsed objects with an existing, exact business "
            "reference. All occurrences of duplicated IDs are excluded. question_lines "
            "includes blank/invalid lines; unique_question_ids counts distinct nonempty "
            "string IDs in parsed objects regardless of business validity. "
            "Question text and as_of_date are not validated in this inventory."
        ),
        "summary": {
            "total_businesses": len(business_dirs),
            "question_lines": question_lines,
            "unique_question_ids": len(seen_question_ids),
            "duplicate_question_ids": len(duplicate_question_ids),
            "total_questions": sum(questions_per_business.values()),
            "total_files": total_files,
            "total_bytes": total_bytes,
            "business_files": biz_files_count,
            "business_bytes": biz_bytes_count,
            "top_level_files": top_level_files,
            "top_level_bytes": top_level_bytes,
            "identical_table_groups": len(identical_table_files),
            "error_count": len(errors_sorted),
        },
        "businesses": businesses_list,
        "identical_table_files": identical_table_files,
        "errors": errors_sorted,
        "files": sorted(list(all_files.values()), key=lambda f: f["path"]),
    }


def generate_markdown(report: dict[str, Any]) -> str:
    """Generate deterministic GitHub Flavored Markdown inventory report."""
    summary = report["summary"]
    lines: list[str] = [
        "# DataMate — Báo cáo kiểm kê cấu trúc dữ liệu",
        "",
        f"- **Thư mục đầu vào:** `{report['input_dir']}`",
        f"- **Thời gian kiểm kê (UTC):** `{report['created_at_utc']}`",
        (
            "- **Phạm vi kiểm kê:** Cấu trúc file, business, phân bố phần mở rộng và câu hỏi. "
            "Chỉ dùng ID/business_id từ câu hỏi, không phân tích bảng/cell hoặc parse gold; "
            "mọi file được hash nhị phân."
        ),
        f"- **Quy tắc đếm câu hỏi:** {report['question_count_policy']}",
        "",
        "## 1. Tổng quan (Summary)",
        "",
        "| Chỉ số | Giá trị |",
        "|---|---|",
        f"| Tổng số doanh nghiệp (business) | {summary['total_businesses']} |",
        f"| Số dòng questions.jsonl (kể cả dòng lỗi/trống) | {summary['question_lines']:,} |",
        f"| Số ID phân biệt trong object đã parse | {summary['unique_question_ids']:,} |",
        f"| Số ID bị lặp (loại mọi lần xuất hiện) | {summary['duplicate_question_ids']:,} |",
        f"| Tổng số câu hỏi hợp lệ (questions) | {summary['total_questions']:,} |",
        f"| Tổng số file kiểm kê | {summary['total_files']:,} |",
        f"| Tổng dung lượng (bytes) | {_format_bytes(summary['total_bytes'])} |",
        f"| Số file trong thư mục business | {summary['business_files']:,} |",
        f"| Dung lượng trong business (bytes) | {_format_bytes(summary['business_bytes'])} |",
        f"| Số file cấp cao nhất (top-level) | {summary['top_level_files']:,} |",
        f"| Dung lượng cấp cao nhất (bytes) | {_format_bytes(summary['top_level_bytes'])} |",
        f"| Số nhóm file bảng trùng SHA-256 | {summary['identical_table_groups']} |",
        f"| Số lỗi cấu trúc phát hiện | {summary['error_count']} |",
        "",
        "## 2. Thống kê theo từng doanh nghiệp (Per-business Breakdown)",
        "",
        "| Business ID | Số câu hỏi | Số file | Dung lượng | Phân bố phần mở rộng |",
        "|---|---|---|---|---|",
    ]

    for biz in report["businesses"]:
        ext_str = (
            ", ".join(
                f"`{ext}`: {cnt}" for ext, cnt in biz["extension_distribution"].items()
            )
            or "none"
        )
        lines.append(
            f"| `{biz['business_id']}` | {biz['question_count']} | {biz['file_count']} | "
            f"{_format_bytes(biz['total_bytes'])} | {ext_str} |"
        )

    lines.extend(
        [
            "",
            "## 3. Nhóm file bảng giống hệt nhau theo SHA-256 (Identical Table Files)",
            "",
            "> [!NOTE]",
            "> Ghi nhận quan sát kỹ thuật: các file bảng dưới đây có cùng mã băm SHA-256 và kích thước byte. "
            "Báo cáo chỉ ghi nhận sự trùng khớp byte thực tế, không tự kết luận các doanh nghiệp là trùng lặp hoặc bản sao của nhau.",
            "",
        ]
    )

    if not report["identical_table_files"]:
        lines.append("Không phát hiện file bảng nào có cùng mã băm SHA-256.")
    else:
        for idx, group in enumerate(report["identical_table_files"], 1):
            lines.append(
                f"### Nhóm {idx}: SHA-256 `{group['sha256']}` ({_format_bytes(group['size_bytes'])})"
            )
            lines.append(
                f"- **Doanh nghiệp liên quan:** {', '.join(f'`{b}`' for b in group['businesses'])}"
            )
            lines.append("- **Danh sách file:**")
            for fpath in group["files"]:
                lines.append(f"  - `{fpath}`")
            lines.append("")

    lines.extend(
        [
            "## 4. Lỗi cấu trúc phát hiện (Structured Errors)",
            "",
        ]
    )

    if not report["errors"]:
        lines.append(
            "Không phát hiện lỗi cấu trúc (JSONL hợp lệ, ID duy nhất, không có tham chiếu doanh nghiệp sai)."
        )
    else:
        lines.extend(
            [
                "| Dòng | Loại lỗi | Question ID | Business ID | Thông báo lỗi |",
                "|---|---|---|---|---|",
            ]
        )
        for err in report["errors"]:
            line_val = str(err.get("line") or "-")
            err_type = f"`{err.get('type', '')}`"
            qid_val = f"`{err['question_id']}`" if err.get("question_id") else "-"
            bid_val = f"`{err['business_id']}`" if err.get("business_id") else "-"
            msg_val = err.get("message", "").replace("|", "\\|")
            lines.append(
                f"| {line_val} | {err_type} | {qid_val} | {bid_val} | {msg_val} |"
            )

    lines.extend(
        [
            "",
            "## 5. Danh sách file kiểm kê (File Inventory)",
            "",
            "| Đường dẫn tương đối | Kích thước (bytes) | SHA-256 |",
            "|---|---|---|",
        ]
    )

    for item in report["files"]:
        lines.append(
            f"| `{item['path']}` | {item['size_bytes']:,} | `{item['sha256']}` |"
        )

    lines.append("")
    return "\n".join(lines)


def run_inventory(input_dir: Path, output_dir: Path) -> dict[str, Any]:
    """Execute inventory and write inventory.json and inventory.md.

    Requires a new output directory outside input, resolving filesystem aliases.
    """
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    if output_dir.is_relative_to(input_dir):
        raise ValueError("Output directory must be outside input directory")
    if output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {output_dir}")

    report = build_inventory(input_dir)

    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / "inventory.json"
    md_path = output_dir / "inventory.md"

    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(generate_markdown(report), encoding="utf-8")

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mechanical data inventory by business (timeline group A)."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to input split directory (e.g. data/train)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to output directory (e.g. runs/p01-inventory)",
    )

    args = parser.parse_args(argv)

    if not args.input.exists() or not args.input.is_dir():
        sys.stderr.write(
            f"Error: input directory not found or not a directory: {args.input}\n"
        )
        return 1

    try:
        report = run_inventory(args.input, args.output)
    except FileExistsError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1
    except Exception as exc:
        sys.stderr.write(f"Error executing inventory: {exc}\n")
        return 1

    summary = report["summary"]
    print(f"Inventory completed for {args.input}:")
    print(f"  - Businesses: {summary['total_businesses']}")
    print(f"  - Questions:  {summary['total_questions']}")
    print(
        f"  - Files:      {summary['total_files']} ({_format_bytes(summary['total_bytes'])})"
    )
    print(f"  - Duplicate table groups: {summary['identical_table_groups']}")
    print(f"  - Structured errors:      {summary['error_count']}")
    print(
        f"Output saved to:\n  - {args.output / 'inventory.json'}\n  - {args.output / 'inventory.md'}"
    )
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
