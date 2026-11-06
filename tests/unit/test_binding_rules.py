from datamate.domain_lib.binding_rules import classify_row, inspect_rows, propose
from datamate.domain_lib.orders import RawRow


def unit():
    labels = ["Mã đơn", "Ngày đặt", "Trạng thái", "SL", "Đơn giá", "Tiền", "Sản phẩm"]
    return dict(
        sql_name="raw_" + "a" * 24,
        source_file="orders.csv",
        source_name="orders",
        header_status="auto_rule",
        data_start_row=2,
        row_count=3,
        columns=[
            dict(sql_name=f"c{i:04}", header_cells=[{"source_row": 1, "cell": label}])
            for i, label in enumerate(labels, 1)
        ],
    )


def readme(net="thành tiền sau giảm"):
    return f"## Cột trong `orders.csv`\n- **Mã đơn**: mã đơn\n- **Ngày đặt**: ngày bán\n- **Trạng thái**: trạng thái đơn\n- **SL**: số lượng\n- **Đơn giá**: đơn giá\n- **Tiền**: {net}\n- **Sản phẩm**: tên hàng\n"


def rows():
    return [
        RawRow(
            i + 2,
            dict(
                c0001=f"A{i}",
                c0002="01/11/2026",
                c0003="Hoàn thành",
                c0004="2",
                c0005="1,000",
                c0006="2000",
                c0007="Tea",
            ),
        )
        for i in range(20)
    ]


def test_semantic_net_proof_is_required_even_with_perfect_arithmetic():
    candidate = propose(unit(), readme("thành tiền trước giảm"))
    check = inspect_rows(rows(), candidate)
    assert check["count_format_ok"]
    assert (
        not check["revenue_format_ok"] and "net_semantics_missing" in check["reasons"]
    )


def test_extra_vat_shipping_or_voucher_semantics_are_not_net():
    for definition in [
        "thành tiền sau giảm + VAT + shipping",
        "thành tiền sau giảm rồi trừ voucher toàn đơn",
    ]:
        check = inspect_rows(rows(), propose(unit(), readme(definition)))
        assert (
            not check["revenue_format_ok"]
            and "net_semantics_missing" in check["reasons"]
        )


def test_arithmetic_can_discriminate_money_scale_but_never_invent_semantics():
    candidate = propose(unit(), readme())
    check = inspect_rows(rows(), candidate)
    assert check["date_format"] == "%d/%m/%Y"
    assert check["number_format"] == "en" and check["revenue_format_ok"]
    assert check["arithmetic"]["en"]["matched"] == 20


def test_equivalent_arithmetic_with_different_money_values_stays_ambiguous():
    data = [
        RawRow(i + 2, r.cells | {"c0004": "1", "c0005": "1,000", "c0006": "1,000"})
        for i, r in enumerate(rows())
    ]
    check = inspect_rows(data, propose(unit(), readme()))
    assert check["count_format_ok"] and not check["revenue_format_ok"]
    assert "number_scale_ambiguous" in check["reasons"]


def test_one_informative_row_cannot_establish_money_scale():
    data = [
        RawRow(i + 2, r.cells | {"c0004": "1", "c0005": "1,000", "c0006": "1,000"})
        for i, r in enumerate(rows()[:9])
    ]
    data.append(
        RawRow(11, rows()[0].cells | {"c0004": "2", "c0005": "1000", "c0006": "2,000"})
    )
    check = inspect_rows(data, propose(unit(), readme()))
    assert not check["revenue_format_ok"]
    assert check["informative_arithmetic_rows"] == 1


def test_unknown_status_and_missing_net_do_not_get_dropped():
    check = inspect_rows(
        [RawRow(2, rows()[0].cells | {"c0003": "Đang giao dịch"})],
        propose(unit(), readme()),
    )
    assert not check["count_format_ok"] and check["unknown_status_rows"] == 1
    check = inspect_rows(
        [RawRow(2, rows()[0].cells | {"c0006": None})], propose(unit(), readme())
    )
    assert check["count_format_ok"] and not check["revenue_format_ok"]


def test_repeated_header_and_printed_total_are_distinct_from_data():
    candidate = propose(unit(), readme())
    header = RawRow(
        40, {c["sql_name"]: c["header_cells"][0]["cell"] for c in unit()["columns"]}
    )
    assert classify_row(header, candidate) == "repeated_header"
    total = RawRow(
        41,
        {f"c{i:04}": None for i in range(1, 8)}
        | {"c0001": "Tổng cộng", "c0006": "2000"},
    )
    assert classify_row(total, candidate) == "printed_total"
    assert (
        classify_row(
            RawRow(42, total.cells | {"c0002": "01/11/2026", "c0003": "Hoàn thành"}),
            candidate,
        )
        == "data"
    )
