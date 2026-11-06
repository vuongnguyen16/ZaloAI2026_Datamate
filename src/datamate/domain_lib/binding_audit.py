"""CPU data checks and local-only binding evidence; never calls model or gold IO."""

import os
import re
import sys
import time
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .binding_rules import classify_row, inspect_rows, norm, propose
from .model import DomainAbstain
from .orders import Binding, BoundSource, adapt_sources
from .raw_reader import open_business


def peak_rss_bytes():
    if os.name != "nt":
        import resource

        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value if sys.platform == "darwin" else value * 1024)
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (k, ctypes.c_size_t)
            for k in [
                "PeakWorkingSetSize",
                "WorkingSetSize",
                "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage",
                "PagefileUsage",
                "PeakPagefileUsage",
            ]
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(Counters),
        wintypes.DWORD,
    ]
    info = Counters()
    info.cb = ctypes.sizeof(info)
    if not psapi.GetProcessMemoryInfo(
        kernel.GetCurrentProcess(), ctypes.byref(info), info.cb
    ):
        raise OSError("cannot measure process working set")
    return int(info.PeakWorkingSetSize)


def data_rows(business, candidate, counts, samples, budget, max_rows):
    col = candidate.columns
    can_carry = False
    last_id = None
    for row in business.iter_rows(candidate.unit):
        budget[0] += 1
        if budget[0] > max_rows:
            raise DomainAbstain("row_resource_or_coordinate")
        kind = classify_row(row, candidate)
        counts[kind] += 1
        if kind != "data":
            can_carry = False
            last_id = None
            continue
        qid = (row.cells.get(col.get("id")) or "").strip()
        has_product = bool((row.cells.get(col.get("product")) or "").strip())
        if not qid:
            if not can_carry or candidate.role != "lines" or not has_product:
                raise DomainAbstain("unresolved_order_row")
        elif not can_carry or qid != last_id:
            if not all(
                (row.cells.get(col.get(k)) or "").strip() for k in ("day", "status")
            ):
                raise DomainAbstain("missing_group_metadata")
            last_id = qid
        can_carry = True
        if len(samples) < 3:
            samples.append(
                dict(
                    row=row.row,
                    values={
                        k: row.cells.get(c)
                        for k, c in col.items()
                        if k
                        in {"id", "day", "status", "qty", "price", "amount", "discount"}
                    },
                )
            )
        yield row


def audit_business(
    index: Path,
    source: Path,
    business_id: str,
    *,
    max_rows=200000,
    max_bytes=128 * 1024**2,
):
    started = time.perf_counter()
    result = dict(
        business_id=business_id,
        count_checked=False,
        revenue_checked=False,
        review_status="machine_checks_failed",
        candidates=[],
        reason=None,
        gold_read=False,
        metric_scope="unfiltered only; no question/inference or PA acceptance",
    )
    try:
        with open_business(index, source, business_id) as business:
            candidates = [
                propose(t, business.readme) for t in business.schema["tables"]
            ]
            valid = [c for c in candidates if not c.reasons]
            lines = [c for c in valid if c.role == "lines"]
            headers = [c for c in valid if c.role == "headers"]
            if not valid:
                raise DomainAbstain("no_order_candidate")
            if lines and headers:
                raise DomainAbstain("ambiguous_order_grains")
            selected = lines or headers

            def family(candidate):
                return re.sub(
                    r"\d+$", "", norm(Path(candidate.unit["source_file"]).stem)
                )

            families = {family(c) for c in selected}
            if any(
                c.reasons
                and family(c) in families
                and ("id" in c.columns or c.unit.get("header_status") == "unresolved")
                for c in candidates
            ):
                raise DomainAbstain("unbound_order_partition")
            return_sources = [
                t
                for t in business.schema["tables"]
                if "trahang" in norm(t["source_file"] + t["source_name"])
            ]
            if return_sources:
                raise DomainAbstain("unbound_return_source")
            budget = [0]
            source_sha = {
                r["path"]: r["sha256"] for r in business.profile["provenance"]["files"]
            }
            bound = []
            for candidate in selected:
                counts = Counter()
                samples = []
                checks = inspect_rows(
                    data_rows(business, candidate, counts, samples, budget, max_rows),
                    candidate,
                )
                result["candidates"].append(
                    dict(
                        unit=candidate.unit["sql_name"],
                        source_file=candidate.unit["source_file"],
                        source_name=candidate.unit["source_name"],
                        role=candidate.role,
                        columns=candidate.columns,
                        semantic_evidence=candidate.evidence,
                        checks=checks,
                        row_kinds=dict(counts),
                        samples=samples,
                        printed_total_comparison="not_comparable_scope_unproven",
                    )
                )
                if checks["count_format_ok"]:
                    b = Binding(
                        candidate.role,
                        candidate.columns["id"],
                        candidate.columns["day"],
                        candidate.columns["status"],
                        candidate.columns.get("amount")
                        if checks["revenue_format_ok"]
                        else None,
                        checks["status_values"],
                        carry_order_fields=True,
                        date_format=checks["date_format"],
                        number_format=checks["number_format"] or "plain",
                    )
                    bound.append((candidate, b))
            if len(bound) != len(selected):
                raise DomainAbstain("binding_data_checks_failed")
            budget = [0]
            sources = [
                BoundSource(
                    c.unit["sql_name"],
                    source_sha[c.unit["source_file"]],
                    b,
                    data_rows(business, c, Counter(), [], budget, max_rows),
                )
                for c, b in bound
            ]
            ledger_started = time.perf_counter()
            ledger = adapt_sources(sources, max_rows=max_rows, max_bytes=max_bytes)
            result["ledger_seconds"] = time.perf_counter() - ledger_started
            if any(
                business.consumed.get(c.unit["sql_name"]) != c.unit["row_count"]
                for c in selected
            ):
                raise DomainAbstain("incomplete_source_coverage")
            result.update(
                count_checked=True,
                revenue_checked=bool(lines)
                and all(c["checks"]["revenue_format_ok"] for c in result["candidates"]),
                review_status="machine_checked_pending_independent_review",
                ledger_orders=len(ledger.orders),
                ledger_lines=sum(len(o.lines) for o in ledger.orders),
                ledger_extent=asdict(ledger.extent),
                provenance=business.proof,
                selected_source_hashes=ledger.provenance,
            )
            match = re.search(
                r"đến hết\s+(\d{1,2}/\d{1,2}/\d{4})", business.readme, re.IGNORECASE
            )
            try:
                expected = (
                    datetime.strptime(match[1], "%d/%m/%Y").date() if match else None
                )
            except ValueError:
                expected = None
            result["readme_end_diagnostic"] = (
                "not_available"
                if expected is None
                else "matched"
                if expected == ledger.extent.end
                else "mismatch_not_automatically_repaired"
            )
    except DomainAbstain as exc:
        result.update(
            count_checked=False,
            revenue_checked=False,
            reason=exc.code,
            review_status="machine_checks_failed",
        )
    result.update(
        elapsed_seconds=time.perf_counter() - started,
        peak_rss_bytes=peak_rss_bytes(),
        memory_method="process lifetime peak working set on Windows; ru_maxrss elsewhere; includes Python/DuckDB/artifact verification",
    )
    return result
