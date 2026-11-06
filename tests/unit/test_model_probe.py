import hashlib
from datetime import datetime, timedelta, timezone

import pytest


def api():
    from datamate import model_probe

    return model_probe


def candidate():
    return {
        "repository": "Synthetic/Small",
        "full_commit_revision": "a" * 40,
        "parameters": 1000,
        "public_release_date": "2025-01-01",
        "snapshot_timestamp": "2025-01-02T00:00:00+00:00",
        "license": "Apache-2.0",
        "eligibility_verified": True,
        "files": {"config.json": hashlib.sha256(b"{}").hexdigest()},
        "sources": ["https://huggingface.co/Synthetic/Small"],
    }


def configuration():
    return {
        "profile": "vuonghungnguyen07",
        "workspace": "vuonghungnguyen07",
        "budget_usd": 30.0,
        "estimated_cost_usd": 10.0,
        "gpu": "RTX-PRO-6000",
        "memory_budget_bytes": 30 * 1024**3,
        "seed": 0,
        "max_model_len": 2048,
        "max_tokens": 256,
        "gpu_timeout_seconds": 1200,
        "startup_timeout_seconds": 1200,
        "staging_timeout_seconds": 3600,
    }


NOW = datetime(2026, 11, 6, tzinfo=timezone.utc)


def check(config=None, model=None, account=None, billing=None):
    module = api()
    return module.preflight(
        module.ProbeConfig.model_validate(config or configuration()),
        module.ModelCandidate.model_validate(model or candidate()),
        account or {"workspace": "vuonghungnguyen07", "user": "vuonghungnguyen07"},
        billing
        or {
            "available_usd": 30.0,
            "checked_at": NOW.isoformat(),
            "source": "user-confirmed",
        },
        now=NOW,
        profile_env="vuonghungnguyen07",
    )


def test_preflight_returns_no_credentials_and_stable_model_identity():
    result = check()
    assert result["model_revision"] == "a" * 40
    assert result["workspace"] == "vuonghungnguyen07"
    assert result["budget_usd"] == 30
    assert "token" not in str(result).lower()


@pytest.mark.parametrize(
    "account",
    [
        {"workspace": "another", "user": "vuonghungnguyen07"},
        {"workspace": "vuonghungnguyen07", "user": "another"},
    ],
)
def test_wrong_live_identity_is_rejected(account):
    with pytest.raises(ValueError, match="account"):
        check(account=account)


@pytest.mark.parametrize(
    "change",
    [
        {"budget_usd": 30.01},
        {"budget_usd": float("nan")},
        {"budget_usd": 0.0},
        {"estimated_cost_usd": 31.0},
        {"gpu": "H100"},
        {"memory_budget_bytes": 31 * 1024**3},
        {"max_tokens": 4096},
        {"seed": 1},
    ],
)
def test_resource_policy_refuses_unsafe_configuration(change):
    with pytest.raises(ValueError):
        check(config=configuration() | change)


@pytest.mark.parametrize(
    "billing",
    [
        {
            "available_usd": 5.0,
            "checked_at": NOW.isoformat(),
            "source": "user-confirmed",
        },
        {
            "available_usd": float("inf"),
            "checked_at": NOW.isoformat(),
            "source": "user-confirmed",
        },
        {
            "available_usd": 30.0,
            "checked_at": (NOW - timedelta(hours=25)).isoformat(),
            "source": "dashboard",
        },
        {
            "available_usd": 30.0,
            "checked_at": (NOW + timedelta(hours=1)).isoformat(),
            "source": "dashboard",
        },
        {"available_usd": 30.0, "checked_at": NOW.isoformat(), "source": "guess"},
    ],
)
def test_billing_must_be_fresh_finite_and_cover_estimate(billing):
    with pytest.raises(ValueError, match="billing"):
        check(billing=billing)


@pytest.mark.parametrize(
    "change",
    [
        {"full_commit_revision": "main"},
        {"parameters": 15_000_000_001},
        {"parameters": True},
        {"eligibility_verified": False},
        {"snapshot_timestamp": "2026-10-01T00:00:00+00:00"},
        {"public_release_date": "2026-10-01"},
        {"license": "unknown"},
        {"files": {"../escape": "a" * 64}},
        {"files": {"x": "bad-hash"}},
        {"files": {"C:/escape": "a" * 64}},
        {"files": {}},
    ],
)
def test_unverified_or_ineligible_model_is_rejected(change):
    with pytest.raises(ValueError):
        check(model=candidate() | change)


def test_explicit_profile_is_required():
    m = api()
    with pytest.raises(ValueError, match="profile"):
        m.preflight(
            m.ProbeConfig(**configuration()),
            m.ModelCandidate(**candidate()),
            {"workspace": "vuonghungnguyen07", "user": "vuonghungnguyen07"},
            {
                "available_usd": 30.0,
                "checked_at": NOW.isoformat(),
                "source": "dashboard",
            },
            now=NOW,
            profile_env="another",
        )


def test_snapshot_hash_and_missing_file_fail_closed(tmp_path):
    module = api()
    files = {"config.json": hashlib.sha256(b"{}").hexdigest()}
    with pytest.raises(ValueError, match="snapshot"):
        module.verify_snapshot(tmp_path, files)
    (tmp_path / "config.json").write_bytes(b"{}")
    assert module.verify_snapshot(tmp_path, files) == files
    (tmp_path / "config.json").write_bytes(b"changed")
    with pytest.raises(ValueError, match="snapshot"):
        module.verify_snapshot(tmp_path, files)


def test_snapshot_does_not_follow_symlink_outside_snapshot(tmp_path):
    module = api()
    source = tmp_path / "source"
    source.mkdir()
    outside = tmp_path / "outside"
    outside.write_bytes(b"{}")
    try:
        (source / "config.json").symlink_to(outside)
    except OSError:
        pytest.skip("OS cannot create synthetic symlink")
    with pytest.raises(ValueError, match="snapshot"):
        module.verify_snapshot(
            source, {"config.json": hashlib.sha256(b"{}").hexdigest()}
        )
