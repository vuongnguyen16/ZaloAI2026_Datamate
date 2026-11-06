import json
from datetime import datetime, timezone

import pytest


def arguments(tmp_path):
    billing = tmp_path / "billing.json"
    billing.write_text(
        json.dumps(
            {
                "available_usd": 30.0,
                "checked_at": "2026-11-06T06:53:37+00:00",
                "source": "user-confirmed",
            }
        )
    )
    return ["check", "--model", "Qwen/Qwen3-14B", "--billing-json", str(billing)]


def test_check_cli_never_constructs_cloud_transport(tmp_path, monkeypatch, capsys):
    from scripts.p1_probe import main

    monkeypatch.setenv("MODAL_PROFILE", "vuonghungnguyen07")

    def forbidden():
        pytest.fail("cloud transport constructed by read-only check")

    result = main(
        arguments(tmp_path),
        account_reader=lambda: {
            "workspace": "vuonghungnguyen07",
            "user": "vuonghungnguyen07",
        },
        transport_factory=forbidden,
        now=datetime(2026, 11, 6, 7, tzinfo=timezone.utc),
    )
    assert result == 0
    assert json.loads(capsys.readouterr().out)["modal_job_launched"] is False


def test_cli_refuses_missing_explicit_profile_before_live_account(
    tmp_path, monkeypatch
):
    from scripts.p1_probe import main

    monkeypatch.delenv("MODAL_PROFILE", raising=False)

    def forbidden():
        pytest.fail("account read before explicit profile")

    with pytest.raises(ValueError, match="profile"):
        main(arguments(tmp_path), account_reader=forbidden)
