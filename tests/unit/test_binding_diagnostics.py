from datamate.domain_lib.binding_diagnostics import aggregate_patterns, diagnose_sources


def unit(name, definitions):
    return dict(
        sql_name=name,
        source_file=f"{name}.csv",
        source_name=name,
        header_status="auto_rule",
        data_start_row=2,
        row_count=3,
        columns=[
            dict(sql_name=f"c{i:04}", declared_name=label)
            for i, label in enumerate(definitions, 1)
        ],
    )


def docs(name, definitions):
    return f"## Cột trong `{name}.csv`\n" + "".join(
        f"- **{label}**: {meaning}\n" for label, meaning in definitions.items()
    )


def test_diagnosis_keeps_join_and_semantic_blockers_per_metric():
    h = {"Order": "mã đơn", "Day": "ngày bán", "State": "trạng thái đơn"}
    d = {"Order": "mã đơn", "Product": "tên hàng", "Net": "tổng thanh toán gồm VAT"}
    units = [unit("heads", h), unit("lines", d)]
    result = diagnose_sources(units, docs("heads", h) + docs("lines", d))
    assert {b["category"] for b in result["metric_blockers"]["revenue_total"]} == {
        "a",
        "c",
    }
    assert all(
        b["reason"] != "net_semantics_missing"
        for b in result["metric_blockers"]["order_count"]
    )
    assert not result["capabilities_granted"]


def test_repetition_counts_distinct_businesses_and_clusters_not_sheets():
    records = [
        dict(
            business_id="one",
            cluster="C1",
            sources=[dict(pattern="header_detail")] * 20,
        )
    ]
    result = aggregate_patterns(records)
    assert result["header_detail"] == dict(
        businesses=1, clusters=1, rule_eligible=False
    )
    records += [
        dict(business_id="two", cluster="C2", sources=[dict(pattern="header_detail")])
    ]
    assert aggregate_patterns(records)["header_detail"] == dict(
        businesses=2, clusters=2, rule_eligible=True
    )


def test_missing_day_and_no_order_key_is_not_exclusion_evidence():
    definitions = {"Whatever": "nghĩa chưa biết"}
    result = diagnose_sources(
        [unit("mystery", definitions)], docs("mystery", definitions)
    )
    assert result["metric_blockers"]["order_count"]
    assert result["sources"][0]["kind"] == "unresolved"


def test_conversion_dictionary_never_overrides_conflicting_order_header():
    meanings = {
        "Mã đơn": "tên hàng",
        "Pack": "đơn vị lớn (thùng, hộp, tấn...)",
        "Factor": "hệ số: số đơn vị cơ bản trong 1 đơn vị lớn",
        "Base": "đơn vị cơ bản",
    }
    result = diagnose_sources([unit("unsafe", meanings)], docs("unsafe", meanings))
    assert result["sources"][0]["kind"] == "unresolved"
    assert result["metric_blockers"]["order_count"]


def test_registered_conversion_annotation_is_compatible_with_product_label():
    meanings = {
        "Tên sản phẩm": "tên hàng (file chỉ có mặt hàng có đơn vị lớn)",
        "Đơn vị quy đổi": "đơn vị lớn (thùng, hộp, tấn...)",
        "Tỉ lệ quy đổi": "hệ số: số đơn vị cơ bản trong 1 đơn vị lớn",
        "Đơn vị cơ bản": "đơn vị cơ bản",
    }
    result = diagnose_sources(
        [unit("conversion", meanings)], docs("conversion", meanings)
    )
    assert result["sources"][0]["kind"] == "conversion"
    assert not result["metric_blockers"]["order_count"]


def test_repeated_unknown_structure_retains_semantic_blocker_and_adds_category_b():
    from datamate.domain_lib.binding_diagnostics import attach_repetition

    meanings = {"Code": "nghĩa chưa biết", "Value": "chưa xác minh"}
    result = diagnose_sources([unit("unknown", meanings)], docs("unknown", meanings))
    records = [
        dict(result, business_id=b, cluster=c)
        for b, c in [("one", "C1"), ("two", "C2")]
    ]
    patterns = aggregate_patterns(records)
    attach_repetition(records, patterns)
    for record in records:
        assert {b["category"] for b in record["metric_blockers"]["order_count"]} == {
            "b",
            "c",
        }
        assert not record["capabilities_granted"]
