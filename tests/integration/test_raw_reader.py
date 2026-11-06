import json
from pathlib import Path

import pytest

from datamate.domain_lib.model import DomainAbstain
from datamate.domain_lib.raw_reader import open_business
from datamate.ingest.loader import ingest_split
from datamate.profile.engine import run_profile


@pytest.fixture
def verified_fixture(tmp_path):
    root = tmp_path / "train"
    biz = root / "data/synthetic_b"
    biz.mkdir(parents=True)
    (biz / "README.md").write_text("# Synthetic fixture\n", encoding="utf-8")
    text = "Mã đơn,Ngày đặt,Trạng thái,Số lượng,Đơn giá,Thành tiền,Ghi chú\nA,2026-11-01,Hoàn thành,1,10,10,original\nB,2026-11-02,Hoàn thành,1,20,20,other\n"
    (biz / "orders.csv").write_text(text, encoding="utf-8")
    (biz / "other.csv").write_text(text, encoding="utf-8")
    report = ingest_split(root, tmp_path / "cache")
    (tmp_path / "ingest").mkdir()
    ingest = tmp_path / "ingest/ingest.json"
    ingest.write_text(json.dumps(report), encoding="utf-8")
    output = tmp_path / "profile"
    run_profile(root, ingest, output)
    return root, output / "profile.json", biz / "orders.csv"


def test_verified_reader_preserves_every_original_cell_and_coordinate(verified_fixture):
    root, index, _ = verified_fixture
    with open_business(index, root, "synthetic_b") as business:
        unit = business.schema["tables"][0]
        rows = list(business.iter_rows(unit))
        assert len(rows) == 3 and rows[0].row == 1
        assert rows[1].cells["c0007"] == "original"
        assert "__row" not in rows[1].cells
        assert business.consumed[unit["sql_name"]] == 3
        assert business.readme.startswith("# Synthetic")


def test_forged_schema_hash_rejected_before_rows(verified_fixture):
    root, index, _ = verified_fixture
    data = json.loads(index.read_text("utf-8"))
    data["businesses"][0]["schema"]["sha256"] = "0" * 64
    index.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(DomainAbstain):
        with open_business(index, root, "synthetic_b"):
            pass


def test_changed_source_rejected_and_context_checks_after_read(verified_fixture):
    root, index, source = verified_fixture
    with pytest.raises(DomainAbstain, match="source_changed"):
        with open_business(index, root, "synthetic_b"):
            with source.open("a", encoding="utf-8") as handle:
                handle.write("\n")
    with pytest.raises(DomainAbstain):
        with open_business(index, root, "synthetic_b"):
            pass


def test_new_source_file_before_or_during_read_is_detected(verified_fixture):
    root, index, source = verified_fixture
    added = source.with_name("returns.csv")
    with pytest.raises(DomainAbstain):
        with open_business(index, root, "synthetic_b"):
            added.write_text("order,status\nA,returned\n", encoding="utf-8")
    with pytest.raises(DomainAbstain):
        with open_business(index, root, "synthetic_b"):
            pass


@pytest.mark.parametrize("remove", ["unit", "column", "header", "declared", "boundary"])
def test_self_consistent_profile_cannot_omit_cache_units_or_columns(
    verified_fixture, remove
):
    import hashlib

    from datamate.profile.engine import schema_descriptor

    root, index, _ = verified_fixture
    data = json.loads(index.read_text("utf-8"))
    entry = data["businesses"][0]
    path = Path(entry["profile"]["path"])
    profile = json.loads(path.read_text("utf-8"))
    if remove == "unit":
        profile["units"].pop()
    elif remove == "column":
        profile["units"][0]["columns"].pop()
    elif remove == "header":
        profile["units"][0]["columns"][0]["header_cells"][0]["cell"]["value"] = (
            "forged label"
        )
    elif remove == "boundary":
        profile["units"][0]["header"]["data_start_row"] = 3
    else:
        profile["units"][0]["columns"][0]["declared_name"] = "forged label"
    for kind, value in [("profile", profile), ("schema", schema_descriptor(profile))]:
        target = Path(entry[kind]["path"])
        target.write_text(json.dumps(value), encoding="utf-8")
        entry[kind]["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
    index.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(DomainAbstain):
        with open_business(index, root, "synthetic_b"):
            pass


def test_unlisted_unit_and_partial_iterator_are_not_complete(verified_fixture):
    root, index, _ = verified_fixture
    with open_business(index, root, "synthetic_b") as business:
        unit = business.schema["tables"][0]
        with pytest.raises(DomainAbstain):
            list(business.iter_rows(unit | {"sql_name": "orders; DROP TABLE x"}))
        iterator = business.iter_rows(unit)
        next(iterator)
        iterator.close()
        assert unit["sql_name"] not in business.consumed
