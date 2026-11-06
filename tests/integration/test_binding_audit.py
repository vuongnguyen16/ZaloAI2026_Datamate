import json

import pytest

from datamate.domain_lib.binding_audit import audit_business
from datamate.ingest.loader import ingest_split
from datamate.profile.engine import run_profile


def prepare(tmp_path, unknown=False, missing_part=False, extra_file=None):
    root = tmp_path / "train"
    biz = root / "data/synthetic_b"
    biz.mkdir(parents=True)
    (biz / "README.md").write_text(
        """# Synthetic
## Cột trong `orders.csv`
- **Mã đơn**: mã đơn
- **Ngày đặt**: ngày bán
- **Trạng thái**: trạng thái đơn
- **SL**: số lượng
- **Đơn giá**: đơn giá
- **Tiền**: thành tiền sau giảm
- **Sản phẩm**: tên hàng
## Quy ước
- Dữ liệu có đến hết 02/11/2026.
""",
        encoding="utf-8",
    )
    status = "Mystery" if unknown else "Hoàn thành"
    (biz / "orders.csv").write_text(
        "Mã đơn,Ngày đặt,Trạng thái,SL,Đơn giá,Tiền,Sản phẩm\n"
        + f"A,2026-11-01,{status},1,10,10,Tea\nB,2026-11-02,Hoàn thành,1,20,20,Coffee\n",
        encoding="utf-8",
    )
    if missing_part:
        (biz / "orders_2.csv").write_text(
            "Mã đơn,Ngày đặt,Sản phẩm,Tiền\nC,2026-11-03,Tea,40\n", encoding="utf-8"
        )
    if extra_file:
        (biz / extra_file).write_text(
            "Mã đơn,Ngày đặt,Tiền\nC,2026-11-03,40\n", encoding="utf-8"
        )
    report = ingest_split(root, tmp_path / "cache")
    folder = tmp_path / "ingest"
    folder.mkdir()
    path = folder / "ingest.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    profile = tmp_path / "profile"
    run_profile(root, path, profile)
    return root, profile / "profile.json"


def test_complete_verified_pipeline_and_author_packet_are_not_oracle(tmp_path):
    root, index = prepare(tmp_path)
    result = audit_business(index, root, "synthetic_b")
    assert result["count_checked"] and result["revenue_checked"]
    assert result["review_status"] == "machine_checked_pending_independent_review"
    assert result["ledger_orders"] == 2 and result["ledger_lines"] == 2
    assert result["peak_rss_bytes"] > 0 and result["elapsed_seconds"] > 0


def test_unknown_status_blocks_business_and_resource_failure_never_passes(tmp_path):
    root, index = prepare(tmp_path, unknown=True)
    result = audit_business(index, root, "synthetic_b")
    assert not result["count_checked"] and not result["revenue_checked"]
    assert any("unknown_status" in c["checks"]["reasons"] for c in result["candidates"])


def test_resource_limit_is_not_a_truncated_checked_ledger(tmp_path):
    root, index = prepare(tmp_path)
    result = audit_business(index, root, "synthetic_b", max_rows=1)
    assert (
        not result["count_checked"] and result["reason"] == "row_resource_or_coordinate"
    )


@pytest.mark.parametrize("name", ["sales.csv", "returns.csv"])
def test_other_unbound_order_or_return_source_is_not_omitted(tmp_path, name):
    root, index = prepare(tmp_path, extra_file=name)
    result = audit_business(index, root, "synthetic_b")
    assert not result["count_checked"] and not result["revenue_checked"]


def test_unbound_order_part_cannot_be_silently_omitted(tmp_path):
    root, index = prepare(tmp_path, missing_part=True)
    result = audit_business(index, root, "synthetic_b")
    assert not result["count_checked"] and result["reason"] == "unbound_order_partition"
