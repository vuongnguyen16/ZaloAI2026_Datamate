from datamate.domain_lib.binding_diagnostics import blocker_profile, summarize_blockers


def record(name, reasons, *, cluster="C1", complete=False):
    return dict(
        business_id=name,
        cluster=cluster,
        count_checked=False,
        revenue_checked=False,
        inspection=dict(row_scan_complete=complete, ledger_validated=False),
        metric_blockers={
            m: [dict(reason=r) for r in reasons]
            for m in ("order_count", "revenue_total")
        },
    )


def test_status_only_is_observed_potential_not_a_promised_pass():
    result = blocker_profile(
        record("one", ["unknown_status", "binding_data_checks_failed"], complete=True),
        "order_count",
    )
    assert result["families"] == ["status"]
    assert result["after_removing"]["status"]["remaining_observed"] == []
    assert result["after_removing"]["status"]["recheck_required"]
    assert not result["after_removing"]["status"]["proven_pass"]
    assert "ledger" in result["unexecuted_checks"]


def test_single_and_joint_removal_keep_other_and_terminal_failures():
    result = blocker_profile(
        record(
            "one",
            ["unknown_status", "unresolved_source_role", "row_resource_or_coordinate"],
        ),
        "order_count",
    )
    assert set(result["families"]) == {"status", "source", "resource"}
    assert result["after_removing"]["status_and_source"]["remaining_observed"] == [
        "resource"
    ]
    wrapper = blocker_profile(
        record("two", ["binding_data_checks_failed"]), "order_count"
    )
    assert wrapper["families"] == ["other"]


def test_aggregate_counts_businesses_clusters_and_existing_pass_separately():
    rows = [
        record("a", ["unknown_status"]),
        record("b", ["unresolved_source_role"], cluster="C2"),
        record("c", ["unknown_status", "unresolved_source_role"], cluster="C2"),
    ]
    result = summarize_blockers(rows)
    assert result["order_count"]["observed_status_only"] == dict(
        businesses=1, clusters=1
    )
    assert result["order_count"]["observed_source_only"] == dict(
        businesses=1, clusters=1
    )
    assert result["order_count"]["observed_status_and_source_only"] == dict(
        businesses=1, clusters=1
    )
    assert not result["order_count"]["is_pass_prediction"]


def test_remaining_bucket_retains_resource_only_business_and_cluster():
    rows = [
        record("a", ["unknown_status"]),
        record("b", ["row_resource_or_coordinate"], cluster="C2"),
    ]
    assert summarize_blockers(rows)["order_count"]["remaining_blocked"] == dict(
        businesses=1, clusters=1
    )
