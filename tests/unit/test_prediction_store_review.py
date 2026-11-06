import errno
import os

import pytest

from datamate.prediction_store import publish


@pytest.mark.parametrize("code", [errno.ENOTSUP, errno.EXDEV, errno.ENOSYS])
def test_explicit_exclusive_fallback_preserves_reuse_and_conflicts(
    tmp_path, monkeypatch, code
):
    def unsupported(*args):
        raise OSError(code, "mount has no links")

    monkeypatch.setattr(os, "link", unsupported)
    target = tmp_path / "final"
    outcome = publish(target, b"ours", allow_exclusive_fallback=True)
    assert outcome["mode"] == "non_atomic_exclusive"
    assert target.read_bytes() == b"ours"
    assert publish(target, b"ours", allow_exclusive_fallback=True)["status"] == "reused"
    with pytest.raises(FileExistsError):
        publish(target, b"different", allow_exclusive_fallback=True)
    assert target.read_bytes() == b"ours"


def test_exclusive_fallback_loses_race_without_overwriting_winner(
    tmp_path, monkeypatch
):
    target = tmp_path / "final"

    def racing(*args):
        target.write_bytes(b"winner")
        raise OSError(errno.ENOTSUP, "mount has no links")

    monkeypatch.setattr(os, "link", racing)
    with pytest.raises(FileExistsError):
        publish(target, b"ours", allow_exclusive_fallback=True)
    assert target.read_bytes() == b"winner"
    assert any(p.read_bytes() == b"ours" for p in tmp_path.glob("*.pending"))


def test_permission_error_does_not_select_fallback(tmp_path, monkeypatch):
    def denied(*args):
        raise PermissionError(errno.EACCES, "denied")

    monkeypatch.setattr(os, "link", denied)
    with pytest.raises(PermissionError):
        publish(tmp_path / "final", b"ours", allow_exclusive_fallback=True)
    assert not (tmp_path / "final").exists()
