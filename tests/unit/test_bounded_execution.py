import multiprocessing
import time
from decimal import Decimal

import duckdb
import pytest

from datamate.bounded_execution import Deadline, run_bounded, run_duckdb


def test_deadline_includes_startup_and_finalization_reserve():
    clock = Deadline(time.monotonic() - 9, 10, 2)
    assert clock.work_remaining == 0
    assert 0 < clock.remaining <= 1
    with pytest.raises(ValueError):
        Deadline(time.monotonic(), 1, 2)


def test_actual_readonly_decimal_query_and_external_denial(tmp_path):
    db = tmp_path / "fixture.duckdb"
    with duckdb.connect(str(db)) as con:
        con.execute("CREATE TABLE t AS SELECT 1.0000000000000001::DECIMAL(20,16) AS n")
    result = run_duckdb(db, "SELECT n FROM t", [], 10)
    assert result["status"] == "ok", result
    assert result["value"] == [[Decimal("1.0000000000000001")]]
    assert run_duckdb(db, "CREATE TABLE forbidden(a INT)", [], 10)["status"] == "error"
    assert (
        run_duckdb(db, "SELECT * FROM read_csv(?)", [str(tmp_path / "no.csv")], 10)[
            "status"
        ]
        == "error"
    )


def test_query_output_is_bounded(tmp_path):
    db = tmp_path / "fixture.duckdb"
    duckdb.connect(str(db)).close()
    assert run_duckdb(db, "SELECT * FROM range(10001)", [], 10)["status"] == "error"


def test_timeout_interrupt_and_forced_terminate_leave_no_children(tmp_path):
    before = {p.pid for p in multiprocessing.active_children()}
    result = run_bounded(time.sleep, (30,), 0.3)
    assert result["status"] == "timeout"
    assert result["cleanup"] == "terminated"
    db = tmp_path / "fixture.duckdb"
    duckdb.connect(str(db)).close()
    result = run_duckdb(
        db, "SELECT sum(i*j) FROM range(100000000) x(i), range(100000000) y(j)", [], 2
    )
    assert result["status"] == "timeout"
    assert not ({p.pid for p in multiprocessing.active_children()} - before)
