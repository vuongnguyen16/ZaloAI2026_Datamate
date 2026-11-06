import errno
import os

import pytest

from datamate.prediction_store import RunStore, publish


def test_publish_reuses_identical_and_preserves_conflict(tmp_path):
    target = tmp_path / "final"
    assert publish(target, b"first")["status"] == "published"
    assert publish(target, b"first")["status"] == "reused"
    with pytest.raises(FileExistsError):
        publish(target, b"second")
    assert target.read_bytes() == b"first"
    assert any(p.read_bytes() == b"second" for p in tmp_path.glob("*.pending"))


def test_racing_writer_cannot_be_overwritten(tmp_path, monkeypatch):
    target = tmp_path / "final"
    original = os.link

    def racing(src, dst):
        target.write_bytes(b"racer")
        return original(src, dst)

    monkeypatch.setattr(os, "link", racing)
    with pytest.raises(FileExistsError):
        publish(target, b"ours")
    assert target.read_bytes() == b"racer"


def test_no_replace_fallback_when_links_unsupported(tmp_path, monkeypatch):
    def unsupported(*args):
        raise OSError(errno.ENOTSUP, "no hardlinks")

    monkeypatch.setattr(os, "link", unsupported)
    with pytest.raises(OSError, match="no hardlinks"):
        publish(tmp_path / "final", b"ours")
    assert not (tmp_path / "final").exists()


def test_segments_resume_torn_tail_and_conflicting_ids(tmp_path):
    first = {"id": "a", "type": "number", "answer": 1}
    with RunStore(tmp_path, {"input": "hash", "config": "hash"}) as store:
        store.append(first)
        store.append(first)
        store.append({"id": "b", "type": "abstain"})
    segment = next(tmp_path.glob("segment-*.jsonl"))
    with segment.open("ab") as out:
        out.write(b'{"id":"torn"')
    with RunStore(tmp_path, {"input": "hash", "config": "hash"}) as store:
        assert set(store.recover()) == {"a", "b"}
        assert any(e["kind"] == "torn_tail" for e in store.errors)
        store.append({"id": "a", "type": "number", "answer": 2})
    with RunStore(tmp_path, {"input": "hash", "config": "hash"}) as store:
        assert store.recover()["a"]["reason"] == "checkpoint_conflict"
    with pytest.raises(ValueError, match="identity"):
        with RunStore(tmp_path, {"input": "different"}):
            pass


def test_corrupt_complete_line_and_exclusive_writer(tmp_path):
    with RunStore(tmp_path, {"x": 1}):
        with pytest.raises((OSError, ValueError)):
            with RunStore(tmp_path, {"x": 1}):
                pass
    (tmp_path / "segment-corrupt.jsonl").write_bytes(b"bad\n")
    with RunStore(tmp_path, {"x": 1}) as store:
        assert store.recover() == {}
        assert store.errors[0]["kind"] == "invalid_checkpoint"


def test_foreign_output_and_hardlinked_segment_rejected(tmp_path):
    (tmp_path / "foreign").write_text("preserve")
    with pytest.raises(ValueError, match="foreign"):
        with RunStore(tmp_path, {}):
            pass
    assert (tmp_path / "foreign").read_text() == "preserve"
    clean = tmp_path / "clean"
    with RunStore(clean, {}):
        pass
    os.link(next(clean.glob("segment-*.jsonl")), tmp_path / "alias")
    with pytest.raises(ValueError, match="linked"):
        with RunStore(clean, {}) as store:
            store.recover()
