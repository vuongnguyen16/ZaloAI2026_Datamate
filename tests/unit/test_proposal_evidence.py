from datamate.proposal_evidence import combine_spans, project_readme, project_rulebook


def test_status_projection_finds_late_clause_not_arbitrary_prefix():
    text = (
        "Unrelated\n" * 400
        + "## 8. Cách ghi\n| Trạng thái đơn | hoàn thành, huỷ, trả hàng, đang giao |\n"
    )
    spans, meta = project_rulebook(text, "status")
    assert any("Trạng thái đơn" in s["text"] and s["line_start"] > 400 for s in spans)
    assert meta["omitted"] and "prefix" not in " ".join(s["text"] for s in spans)
    assert all(s["sha256"] for s in spans)


def test_partition_alias_needs_explicit_source_declaration():
    section = "## Cột trong `orders.csv`\n- **Mã**: mã đơn\n"
    spans, meta = project_readme(section, "orders_2026.csv", "sheet")
    assert not spans and meta["required_evidence_missing"]
    spans, meta = project_readme(
        "Danh sách dài tách thành nhiều file.\n" + section, "orders_2026.csv", "sheet"
    )
    assert spans and meta["match"] == "declared_partition"
    assert any("tách thành nhiều file" in s["text"] for s in spans)


def test_sqlite_projection_uses_named_table_references():
    text = "## Bảng\n`orders`, `stock`\n## Quy ước\n- `orders.net` là tiền dòng.\n- `stock.qty` là tồn.\n"
    spans, meta = project_readme(
        text, "pos.sqlite", "orders", database_files=["pos.sqlite"]
    )
    assert meta["match"] == "table_reference"
    assert any("orders.net" in s["text"] for s in spans)
    assert not any("stock.qty" in s["text"] for s in spans)


def test_sqlite_table_name_alone_does_not_establish_file_association():
    text = "## Source: old.sqlite\n- `orders.net` is archive adjustment.\n"
    spans, meta = project_readme(text, "new.sqlite", "orders")
    assert not spans and meta["required_evidence_missing"]


def test_sqlite_multiple_files_require_explicit_file_section():
    text = "## Source: old.sqlite\n- `orders.net` archive\n## Source: new.sqlite\n- `orders.net` current\n"
    spans, meta = project_readme(
        text, "new.sqlite", "orders", database_files=["old.sqlite", "new.sqlite"]
    )
    assert meta["match"] == "file_table_reference"
    assert any("current" in s["text"] for s in spans)
    assert not any("archive" in s["text"] for s in spans)


def test_span_offsets_preserve_true_source_text_and_expose_omissions():
    spans = [
        dict(source="one", sha256="a" * 64, line_start=1, line_end=1, text="first"),
        dict(source="two", sha256="b" * 64, line_start=5, line_end=5, text="second"),
    ]
    evidence, projection = combine_spans(spans, [dict(omitted=True)])
    assert projection["omitted"]
    assert [evidence[s["start"] : s["end"]] for s in projection["spans"]] == [
        "first",
        "second",
    ]
