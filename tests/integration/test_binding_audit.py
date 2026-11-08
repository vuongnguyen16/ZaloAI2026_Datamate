import json
import sqlite3

import pytest

from datamate.domain_lib.binding_audit import audit_business
from datamate.ingest.loader import ingest_split
from datamate.profile.engine import run_profile


def prepare(
    tmp_path,
    unknown=False,
    missing_part=False,
    extra_file=None,
    native=False,
    review_aux=False,
):
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
    if review_aux:
        (biz / "payments.csv").write_text(
            "Mã đơn,Ngày thu,Mã phiếu,Tiền thu\nA,2026-11-02,R1,10\n", encoding="utf-8"
        )
        readme = biz / "README.md"
        readme.write_text(
            readme.read_text("utf-8")
            + "\n## Cột trong "
            + chr(96)
            + "payments.csv"
            + chr(96)
            + "\n- **Mã đơn**: mã đơn\n- **Ngày thu**: thời điểm thu\n- **Mã phiếu**: mã phiếu thu\n- **Tiền thu**: số tiền khách trả lần đó\n",
            encoding="utf-8",
        )
    if native:
        readme = biz / "README.md"
        readme.write_text(
            readme.read_text("utf-8").replace("orders.csv", "orders.sqlite"),
            encoding="utf-8",
        )
        (biz / "orders.csv").unlink()
        con = sqlite3.connect(biz / "orders.sqlite")
        try:
            con.execute(
                'CREATE TABLE orders ("Mã đơn" TEXT,"Ngày đặt" TEXT,"Trạng thái" TEXT,"SL" TEXT,"Đơn giá" TEXT,"Tiền" TEXT,"Sản phẩm" TEXT)'
            )
            con.execute(
                "INSERT INTO orders VALUES (?,?,?,?,?,?,?)",
                ("A", "2026-11-01", "Hoàn thành", "1", "10", "10", "Tea"),
            )
            con.commit()
        finally:
            con.close()
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
    assert result["inspection"]["row_scan_complete"]
    assert result["inspection"]["ledger_validated"]
    assert result["peak_rss_bytes"] > 0 and result["elapsed_seconds"] > 0


def test_native_sqlite_source_schema_can_be_checked(tmp_path):
    root, index = prepare(tmp_path, native=True)
    result = audit_business(index, root, "synthetic_b")
    assert result["count_checked"] and result["revenue_checked"]
    assert result["ledger_orders"] == 1


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
    assert result["inspection"]["uninspected_units"]
    assert not result["inspection"]["row_scan_complete"]
    assert not result["inspection"]["ledger_validated"]


@pytest.mark.parametrize("name", ["sales.csv", "returns.csv"])
def test_other_unbound_order_or_return_source_is_not_omitted(tmp_path, name):
    root, index = prepare(tmp_path, extra_file=name)
    result = audit_business(index, root, "synthetic_b")
    assert not result["count_checked"] and not result["revenue_checked"]


def test_unbound_order_part_cannot_be_silently_omitted(tmp_path):
    root, index = prepare(tmp_path, missing_part=True)
    result = audit_business(index, root, "synthetic_b")
    assert not result["count_checked"] and result["reason"] == "unbound_order_partition"


def test_semantic_inventory_reads_verified_dev_statuses_without_money_or_gold(tmp_path):
    from datamate.domain_lib.raw_reader import open_business
    from datamate.domain_lib.semantic_review import inventory_business

    root, index = prepare(tmp_path, unknown=True)
    with open_business(index, root, "synthetic_b") as business:
        result = inventory_business(business)
    assert result["labels"] == {"Mystery": 1, "Hoàn thành": 1}
    assert result["inventory_complete"]
    assert result["source_decisions"][0]["decision"] == "pending"


def test_reviewed_status_map_is_explicit_and_unseen_labels_still_fail(tmp_path):
    root, index = prepare(tmp_path, unknown=True)
    result = audit_business(
        index, root, "synthetic_b", status_values={"mystery": "completed"}
    )
    assert result["count_checked"] and result["revenue_checked"]
    result = audit_business(
        index, root, "synthetic_b", status_values={"unrelated": "completed"}
    )
    assert not result["count_checked"]


def test_inventory_guard_keeps_all_source_metadata_for_human_review(tmp_path):
    from datamate.domain_lib.raw_reader import open_business
    from datamate.domain_lib.semantic_review import inventory_business

    root, index = prepare(tmp_path, missing_part=True)
    with open_business(index, root, "synthetic_b") as business:
        result = inventory_business(business, max_rows=1)
    assert not result["inventory_complete"]
    assert len(result["source_decisions"]) == 2


def test_review_evidence_hash_identifies_original_readme_bytes(tmp_path):
    import hashlib

    from datamate.domain_lib.raw_reader import open_business
    from datamate.domain_lib.semantic_review import inventory_business

    root, index = prepare(tmp_path)
    digest = hashlib.sha256(
        (root / "data/synthetic_b/README.md").read_bytes()
    ).hexdigest()
    with open_business(index, root, "synthetic_b") as business:
        result = inventory_business(business)
    assert result["source_decisions"][0]["evidence"][0]["sha256"] == digest


def approved_sources(tmp_path, root, index, source_file="payments.csv", stale=False):
    import hashlib

    from datamate.domain_lib.raw_reader import open_business
    from datamate.domain_lib.source_exclusions import (
        load_source_exclusions,
        unit_digest,
    )

    with open_business(index, root, "synthetic_b") as business:
        unit = next(
            u for u in business.schema["tables"] if u["source_file"] == source_file
        )
        hashes = {
            f["path"]: f["sha256"] for f in business.profile["provenance"]["files"]
        }
        record = dict(
            business_id="synthetic_b",
            provenance=business.proof,
            sources=[
                dict(
                    unit=unit["sql_name"],
                    source_file=unit["source_file"],
                    source_name=unit["source_name"],
                    unit_sha256="0" * 64 if stale else unit_digest(unit),
                    source_sha256=hashes[source_file],
                    readme_sha256=hashes["README.md"],
                    role="payments",
                    decision="approved_exclude",
                )
            ],
        )
    value = dict(
        version=1,
        kind="reviewed_source_exclusions",
        partition="dev",
        scope="default_unfiltered",
        metrics=["order_count", "revenue_total"],
        rulebook_sha256="b" * 64,
        reviewed_packet_sha256="c" * 64,
        review=dict(
            state="approved",
            reviewer="human fixture owner",
            reviewed_at="2020-01-01T00:00:00+00:00",
            approval_text="Fixture payment source, unfiltered only",
        ),
        businesses=[record],
    )
    path = tmp_path / "approved-sources.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return load_source_exclusions(
        path, hashlib.sha256(path.read_bytes()).hexdigest(), "b" * 64, {"synthetic_b"}
    )


def test_explicit_approved_auxiliary_source_unlocks_without_claiming_physical_scan(
    tmp_path,
):
    root, index = prepare(tmp_path, review_aux=True)
    review = approved_sources(tmp_path, root, index)
    baseline = audit_business(index, root, "synthetic_b")
    assert not baseline["count_checked"]
    result = audit_business(index, root, "synthetic_b", source_exclusions=review)
    assert result["count_checked"] and result["revenue_checked"]
    assert result["inspection"]["required_row_scan_complete"]
    assert not result["inspection"]["row_scan_complete"]
    assert result["inspection"]["uninspected_units"]
    excluded = [
        u for u in result["unit_coverage"] if u["disposition"] == "excluded_by_review"
    ]
    assert len(excluded) == 1 and excluded[0]["review_sha256"] == review.sha256
    assert not any(
        b.get("unit") == excluded[0]["unit"]
        for b in result["metric_blockers"]["order_count"]
    )
    assert any(
        s["kind"] == "reviewed_exclusion" and s["pattern"] == "unresolved"
        for s in result["sources"]
    )


@pytest.mark.parametrize(
    "options", [dict(unknown=True), dict(extra_file="unreviewed.csv")]
)
def test_exclusion_does_not_bypass_status_or_another_unapproved_source(
    tmp_path, options
):
    root, index = prepare(tmp_path, review_aux=True, **options)
    review = approved_sources(tmp_path, root, index)
    result = audit_business(index, root, "synthetic_b", source_exclusions=review)
    assert not result["count_checked"] and not result["revenue_checked"]


def test_exclusion_never_relaxes_resource_or_stale_or_known_order_checks(tmp_path):
    root, index = prepare(tmp_path, review_aux=True)
    review = approved_sources(tmp_path, root, index)
    result = audit_business(
        index, root, "synthetic_b", source_exclusions=review, max_rows=1
    )
    assert (
        not result["count_checked"] and result["reason"] == "row_resource_or_coordinate"
    )
    for review in [
        approved_sources(tmp_path, root, index, stale=True),
        approved_sources(tmp_path, root, index, source_file="orders.csv"),
    ]:
        result = audit_business(index, root, "synthetic_b", source_exclusions=review)
        assert (
            not result["count_checked"]
            and result["reason"] == "source_exclusion_identity_or_plan_mismatch"
        )
