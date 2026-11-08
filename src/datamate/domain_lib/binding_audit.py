"""CPU data checks and local-only binding evidence; never calls model or gold IO."""

import os
import re
import sys
import time
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .binding_diagnostics import METRICS, blocker, diagnose_sources
from .binding_rules import (
    NUMBER_FORMATS,
    classify_row,
    inspect_rows,
    norm,
)
from .binding_structure import plan_source
from .model import DomainAbstain
from .orders import Binding, BoundSource, RawRow, _money, adapt_sources
from .raw_reader import open_business
from .source_exclusions import match_source_exclusions


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


def data_rows(
    business, candidate, counts, samples, budget, max_rows, *, require_metadata=True
):
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
            if require_metadata and not all(
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


def return_quantity(row, candidate):
    value = (row.cells.get(candidate.columns["return_qty"]) or "").strip()
    outcomes = {
        parsed
        for fmt in NUMBER_FORMATS
        if (
            parsed := _money(
                value, Binding("events", "id", None, "status", number_format=fmt)
            )
        )
        is not None
    }
    if len(outcomes) != 1 or next(iter(outcomes)) < 0:
        raise DomainAbstain("unverified_return_quantity")
    return next(iter(outcomes))


def event_rows(rows, candidate):
    for row in rows:
        if return_quantity(row, candidate) > 0:
            yield RawRow(
                row.row, dict(row.cells) | {"derived_return_status": "returned"}
            )


def audit_business(
    index: Path,
    source: Path,
    business_id: str,
    *,
    max_rows=200000,
    max_bytes=128 * 1024**2,
    status_values=None,
    source_exclusions=None,
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
        inspection=dict(
            row_scan_complete=False,
            required_row_scan_complete=False,
            ledger_validated=False,
            uninspected_units=[],
            approved_excluded_units=[],
        ),
    )
    if source_exclusions is not None:
        result["approved_source_exclusions_sha256"] = source_exclusions.sha256
    try:
        with open_business(index, source, business_id) as business:
            units = business.schema["tables"]
            result["inspection"]["uninspected_units"] = [u["sql_name"] for u in units]
            try:
                excluded = (
                    match_source_exclusions(source_exclusions, business, business_id)
                    if source_exclusions is not None
                    else {}
                )
            except ValueError as exc:
                raise DomainAbstain(
                    "source_exclusion_identity_or_plan_mismatch"
                ) from exc
            result["inspection"]["approved_excluded_units"] = sorted(excluded)
            diagnosis = diagnose_sources(units, business.readme)
            result["sources"] = diagnosis["sources"]
            result["machine_diagnosis_blockers"] = diagnosis["metric_blockers"]
            result["diagnosis_blockers"] = {
                m: [
                    b
                    for b in diagnosis["metric_blockers"][m]
                    if b.get("unit") not in excluded
                ]
                for m in METRICS
            }
            for item in result["sources"]:
                if item["unit"] in excluded:
                    item.update(
                        machine_kind=item["kind"],
                        kind="reviewed_exclusion",
                        pattern="unresolved",
                        reviewed_role=excluded[item["unit"]].role,
                        review_sha256=source_exclusions.sha256,
                        review_scope="default_unfiltered",
                    )
            plans = [plan_source(t, business.readme) for t in units]
            selected = [p for p in plans if p.kind not in {"conversion", "unresolved"}]
            unbound = [
                p.candidate
                for p in plans
                if p.kind == "unresolved"
                and p.candidate.unit["sql_name"] not in excluded
            ]
            headers = [p for p in selected if p.kind == "headers"]
            lines = [p for p in selected if p.candidate.role == "lines"]
            result["metric_blockers"] = {m: [] for m in METRICS}

            def add(reason, *, metrics=METRICS, category="c", unit=None):
                for metric in metrics:
                    result["metric_blockers"][metric].append(
                        blocker(reason, category=category, unit=unit)
                    )

            result["unit_coverage"] = [
                dict(
                    unit=p.candidate.unit["sql_name"],
                    source_file=p.candidate.unit["source_file"],
                    source_name=p.candidate.unit["source_name"],
                    disposition="excluded_by_review"
                    if p.candidate.unit["sql_name"] in excluded
                    else "excluded_conversion_semantics"
                    if p.kind == "conversion"
                    else "unresolved_source_role"
                    if p.kind == "unresolved"
                    else "selected_order_source",
                    **(
                        dict(
                            review_sha256=source_exclusions.sha256,
                            reviewed_role=excluded[p.candidate.unit["sql_name"]].role,
                            scope="default_unfiltered",
                            metrics=list(METRICS),
                        )
                        if p.candidate.unit["sql_name"] in excluded
                        else {}
                    ),
                )
                for p in plans
            ]
            for c in unbound:
                add("unresolved_source_role", unit=c.unit["sql_name"])
                for reason in c.reasons:
                    add(reason, unit=c.unit["sql_name"])
            if not any(p.kind in {"headers", "combined_lines"} for p in selected):
                raise DomainAbstain("no_order_candidate")
            if any(p.kind == "details" for p in selected) and not headers:
                raise DomainAbstain("missing_verified_header")
            budget = [0]
            source_sha = {
                r["path"]: r["sha256"] for r in business.profile["provenance"]["files"]
            }
            bound = []
            header_ids, detail_ids, event_ids, combined_ids = set(), set(), set(), set()
            identity_bytes = 0
            for plan in selected:
                candidate = plan.candidate
                counts, samples = Counter(), []
                joined = plan.kind == "details"

                def rows_with_ids():
                    nonlocal identity_bytes
                    last_id = None
                    for row in data_rows(
                        business,
                        candidate,
                        counts,
                        samples,
                        budget,
                        max_rows,
                        require_metadata=not joined and plan.kind != "return_quantity",
                    ):
                        qid = (
                            row.cells.get(candidate.columns["id"]) or ""
                        ).strip() or last_id
                        if not qid or len(qid) > 512:
                            raise DomainAbstain("missing_or_invalid_order_id")
                        last_id = qid
                        identity_bytes += 64 + len(qid.encode("utf-8"))
                        if identity_bytes > max_bytes:
                            raise DomainAbstain("identity_byte_limit")
                        if plan.kind == "headers":
                            if qid in header_ids:
                                add(
                                    "duplicate_order_header",
                                    category="a",
                                    unit=candidate.unit["sql_name"],
                                )
                            header_ids.add(qid)
                        elif joined:
                            detail_ids.add(qid)
                        elif plan.kind == "return_quantity":
                            event_ids.add(qid)
                        elif plan.kind == "combined_lines":
                            combined_ids.add(qid)
                        yield row

                if plan.kind == "return_quantity":
                    event_count = total = 0
                    for row in rows_with_ids():
                        total += 1
                        event_count += return_quantity(row, candidate) > 0
                    checks = dict(
                        count_format_ok=True,
                        revenue_format_ok=True,
                        status_values={"returned": "returned"},
                        date_format="%Y-%m-%d",
                        number_format="plain",
                        reasons=[],
                        rows=total,
                        returned_rows=event_count,
                    )
                else:
                    checks = inspect_rows(
                        rows_with_ids(),
                        candidate,
                        header_join=joined,
                        status_values=status_values,
                    )
                if (
                    business.consumed.get(candidate.unit["sql_name"])
                    == candidate.unit["row_count"]
                ):
                    result["inspection"]["uninspected_units"].remove(
                        candidate.unit["sql_name"]
                    )
                result["inspection"]["row_scan_complete"] = not result["inspection"][
                    "uninspected_units"
                ]
                result["candidates"].append(
                    dict(
                        unit=candidate.unit["sql_name"],
                        source_file=candidate.unit["source_file"],
                        source_name=candidate.unit["source_name"],
                        role=candidate.role,
                        columns=candidate.columns,
                        semantic_evidence=plan.evidence,
                        checks=checks,
                        row_kinds=dict(counts),
                        samples=samples,
                        printed_total_comparison="not_comparable_scope_unproven",
                    )
                )
                if not checks["count_format_ok"]:
                    for reason in checks["reasons"]:
                        if (
                            reason
                            in {
                                "unknown_status",
                                "missing_status_inventory",
                                "date_format_unverified",
                            }
                            or reason in candidate.reasons
                        ):
                            add(reason, unit=candidate.unit["sql_name"])
                if candidate.role == "lines" and not checks["revenue_format_ok"]:
                    for reason in checks["reasons"]:
                        add(
                            reason,
                            metrics=("revenue_total",),
                            unit=candidate.unit["sql_name"],
                        )
                if checks["count_format_ok"]:
                    binding = Binding(
                        candidate.role,
                        candidate.columns["id"],
                        candidate.columns.get("day"),
                        "derived_return_status"
                        if plan.kind == "return_quantity"
                        else candidate.columns.get("status"),
                        candidate.columns.get("amount")
                        if checks["revenue_format_ok"]
                        else None,
                        checks["status_values"],
                        carry_order_fields=candidate.role == "lines",
                        date_format=checks["date_format"] or "%Y-%m-%d",
                        number_format=checks["number_format"] or "plain",
                    )
                    bound.append((plan, binding))
            if unbound:

                def family(c):
                    return re.sub(r"\d+$", "", norm(Path(c.unit["source_file"]).stem))

                families = {family(p.candidate) for p in selected}
                raise DomainAbstain(
                    "unbound_order_partition"
                    if any(family(c) in families for c in unbound)
                    else "unbound_relevant_source"
                )
            if any(
                b["reason"] == "duplicate_order_header"
                for b in result["metric_blockers"]["order_count"]
            ):
                raise DomainAbstain("duplicate_order_header")
            if len(bound) != len(selected):
                raise DomainAbstain("binding_data_checks_failed")
            if headers and detail_ids - header_ids:
                raise DomainAbstain("orphan_order_detail")
            # Check all event references, including zero-return rows, not only
            # the derived positive events consumed by the ledger.
            if event_ids - (header_ids | combined_ids):
                raise DomainAbstain("orphan_order_event")
            if not lines:
                add("missing_order_details", metrics=("revenue_total",))
            budget = [0]

            def bound_rows(plan):
                candidate = plan.candidate
                rows = data_rows(
                    business,
                    candidate,
                    Counter(),
                    [],
                    budget,
                    max_rows,
                    require_metadata=plan.kind not in {"details", "return_quantity"},
                )
                return (
                    event_rows(rows, candidate)
                    if plan.kind == "return_quantity"
                    else rows
                )

            sources = [
                BoundSource(
                    p.candidate.unit["sql_name"],
                    source_sha[p.candidate.unit["source_file"]],
                    b,
                    bound_rows(p),
                )
                for p, b in bound
            ]
            ledger_started = time.perf_counter()
            ledger = adapt_sources(sources, max_rows=max_rows, max_bytes=max_bytes)
            result["inspection"]["ledger_validated"] = True
            result["ledger_seconds"] = time.perf_counter() - ledger_started
            if any(
                business.consumed.get(p.candidate.unit["sql_name"])
                != p.candidate.unit["row_count"]
                for p in selected
            ):
                raise DomainAbstain("incomplete_source_coverage")
            if lines and any(not o.lines for o in ledger.orders):
                add("header_without_order_details", metrics=("revenue_total",))
            result["inspection"]["required_row_scan_complete"] = True
            result.update(
                count_checked=True,
                revenue_checked=bool(lines)
                and not result["metric_blockers"]["revenue_total"],
                review_status="machine_checked_pending_independent_review",
                ledger_orders=len(ledger.orders),
                ledger_lines=sum(len(o.lines) for o in ledger.orders),
                ledger_extent=asdict(ledger.extent),
                provenance=business.proof,
                selected_source_hashes=ledger.provenance,
                order_status_counts=dict(Counter(o.status for o in ledger.orders)),
                joined_header_orders=len(header_ids),
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
        result["inspection"]["ledger_validated"] = False
        result["inspection"]["required_row_scan_complete"] = False
        metric_blockers = result.setdefault("metric_blockers", {m: [] for m in METRICS})
        for metric in METRICS:
            metric_blockers[metric].append(blocker(exc.code))
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
