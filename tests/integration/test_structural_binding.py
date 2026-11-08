"""Synthetic header/detail/event counterexamples; no real business fixtures."""

import json

import pytest

from datamate.domain_lib.binding_audit import audit_business
from datamate.ingest.loader import ingest_split
from datamate.profile.engine import run_profile


def prepare(
    tmp_path,
    *,
    orphan=False,
    duplicate=False,
    bad_money=False,
    unknown=False,
    conversion=False,
    event_orphan=False,
    combined=False,
    ambiguous_details=False,
    event_metadata=False,
    detail_status=False,
    header_first=False,
):
    root = tmp_path / "train"
    biz = root / "data/synthetic_join"
    biz.mkdir(parents=True)
    readme = """# Synthetic source semantics
## Cột trong `headers.csv`
- **Order**: mã đơn
- **Placed**: ngày bán
- **State**: trạng thái đơn
## Cột trong `details.csv`
- **Order**: mã đơn
- **Product**: tên hàng
- **Quantity**: số lượng
- **Price**: đơn giá
- **Net**: thành tiền sau giảm
## Cột trong `lots.csv`
- **Order**: mã đơn
- **Returned**: số lượng khách trả lại (đơn vị cơ bản); lớn hơn 0: đơn đó có trả hàng
## Cột trong `units.csv`
- **Item**: tên hàng (file chỉ có mặt hàng có đơn vị lớn)
- **Pack**: đơn vị lớn (thùng, hộp, tấn...)
- **Factor**: hệ số: số đơn vị cơ bản trong 1 đơn vị lớn
- **Base**: đơn vị cơ bản
"""
    if ambiguous_details or detail_status:
        readme += "\n## Cột trong `details.csv`\n- **State1**: trạng thái đơn\n"
        if ambiguous_details:
            readme += "- **State2**: trạng thái đơn\n"
    if event_metadata:
        readme += "\n## Cột trong `lots.csv`\n- **State**: trạng thái đơn\n"
    (biz / "README.md").write_text(readme, encoding="utf-8")
    state = "Mystery" if unknown else "Hoàn thành"
    headers = f"Order,Placed,State\nA,2026-11-01,{state}\nB,2026-11-02,Hoàn thành\n"
    if duplicate:
        headers += "A,2026-11-01,Hoàn thành\n"
    (biz / "headers.csv").write_text(headers, encoding="utf-8")
    net = "bad" if bad_money else "10"
    details = f"Order,Product,Quantity,Price,Net\nA,Tea,1,10,{net}\nA,Coffee,2,10,20\nB,Tea,3,10,30\n"
    if orphan:
        details += "X,Tea,1,10,10\n"
    (biz / "details.csv").write_text(details, encoding="utf-8")
    if ambiguous_details or detail_status:
        records = details.splitlines()
        suffix = ",State1,State2" if ambiguous_details else ",State1"
        cells = ",Hoàn thành,Mystery" if ambiguous_details else ",Mystery"
        (biz / "details.csv").write_text(
            records[0]
            + suffix
            + "\n"
            + "".join(line + cells + "\n" for line in records[1:]),
            encoding="utf-8",
        )
    if combined:
        (biz / "headers.csv").unlink()
        (biz / "README.md").write_text(
            readme
            + "\n## Cột trong `details.csv`\n- **Placed**: ngày bán\n- **State**: trạng thái đơn\n",
            encoding="utf-8",
        )
        records = details.splitlines()
        (biz / "details.csv").write_text(
            records[0]
            + ",Placed,State\n"
            + "".join(line + ",2026-11-01,Hoàn thành\n" for line in records[1:]),
            encoding="utf-8",
        )
    (biz / "lots.csv").write_text(
        "Order,Returned\nA,0\nB,1\n" + ("X,0\n" if event_orphan else ""),
        encoding="utf-8",
    )
    if event_metadata:
        (biz / "lots.csv").write_text(
            "Order,Returned,State\nA,0,Hoàn thành\nB,1,Mystery\n", encoding="utf-8"
        )
    if header_first:
        (biz / "headers.csv").rename(biz / "a_headers.csv")
        readme = (
            (biz / "README.md")
            .read_text("utf-8")
            .replace("`headers.csv`", "`a_headers.csv`")
        )
        (biz / "README.md").write_text(readme, encoding="utf-8")
    if conversion:
        (biz / "units.csv").write_text(
            "Item,Pack,Factor,Base\nTea,Box,12,Piece\n", encoding="utf-8"
        )
    report = ingest_split(root, tmp_path / "cache")
    (tmp_path / "ingest").mkdir()
    ingest = tmp_path / "ingest/ingest.json"
    ingest.write_text(json.dumps(report), encoding="utf-8")
    annotation = tmp_path / "headers.json"
    annotation.write_text(
        json.dumps(
            dict(
                version=1,
                selections=[
                    dict(
                        business_id="synthetic_join",
                        ingest_fingerprint=report["businesses"][0]["fingerprint"],
                        source_file=f.name,
                        source_name=f.stem,
                        source_kind="csv",
                        rows=[1],
                    )
                    for f in sorted(biz.glob("*.csv"))
                ],
            )
        ),
        encoding="utf-8",
    )
    output = tmp_path / "profile"
    run_profile(root, ingest, output, header_map=annotation)
    return root, output / "profile.json"


def test_header_detail_and_positive_return_quantity_use_existing_core(tmp_path):
    root, index = prepare(tmp_path, conversion=True)
    result = audit_business(index, root, "synthetic_join")
    assert result["count_checked"] and result["revenue_checked"], result
    assert result["ledger_orders"] == 2 and result["ledger_lines"] == 3
    assert result["order_status_counts"] == {"completed": 1, "returned": 1}
    assert result["joined_header_orders"] == 2
    assert result["review_status"] == "machine_checked_pending_independent_review"


@pytest.mark.parametrize(
    "option,reason",
    [
        ("orphan", "orphan_order_detail"),
        ("duplicate", "duplicate_order_header"),
        ("event_orphan", "orphan_order_event"),
    ],
)
def test_join_and_even_zero_return_rows_cannot_hide_orphans(tmp_path, option, reason):
    root, index = prepare(tmp_path, **{option: True})
    result = audit_business(index, root, "synthetic_join")
    assert not result["count_checked"] and not result["revenue_checked"]
    assert result["reason"] == reason


def test_money_failure_does_not_block_verified_order_count(tmp_path):
    root, index = prepare(tmp_path, bad_money=True)
    result = audit_business(index, root, "synthetic_join")
    assert result["count_checked"] and not result["revenue_checked"], result
    assert result["metric_blockers"]["revenue_total"]
    assert not result["metric_blockers"]["order_count"]


def test_unknown_header_status_blocks_both_metrics(tmp_path):
    root, index = prepare(tmp_path, unknown=True)
    result = audit_business(index, root, "synthetic_join")
    assert not result["count_checked"] and not result["revenue_checked"]
    assert any(
        b["reason"] == "unknown_status"
        for b in result["metric_blockers"]["order_count"]
    )


def test_zero_return_orphan_also_fails_without_separate_headers(tmp_path):
    root, index = prepare(tmp_path, combined=True, event_orphan=True)
    result = audit_business(index, root, "synthetic_join")
    assert not result["count_checked"]
    assert result["reason"] == "orphan_order_event"


@pytest.mark.parametrize("option", ["ambiguous_details", "event_metadata"])
def test_ambiguous_or_mixed_metadata_cannot_be_erased_by_source_role(tmp_path, option):
    root, index = prepare(tmp_path, **{option: True})
    result = audit_business(index, root, "synthetic_join")
    assert not result["count_checked"] and not result["revenue_checked"]
    assert result["metric_blockers"]["order_count"]


def test_duplicate_header_keeps_later_independent_status_and_money_blockers(tmp_path):
    root, index = prepare(
        tmp_path, duplicate=True, detail_status=True, bad_money=True, header_first=True
    )
    result = audit_business(index, root, "synthetic_join")
    reasons = {b["reason"] for b in result["metric_blockers"]["order_count"]}
    assert {"duplicate_order_header", "unknown_status"} <= reasons
    assert "amount_format_unverified" in {
        b["reason"] for b in result["metric_blockers"]["revenue_total"]
    }
