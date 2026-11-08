import hashlib
import json
from datetime import datetime, timezone

import pytest

from datamate.domain_lib.semantic_review import draft_lexicon, load_approved_lexicon


def draft():
    return draft_lexicon(
        [
            dict(
                business_id="synthetic",
                cluster="C1",
                labels={"Custom": 2},
                status_sources=[],
                source_decisions=[],
            )
        ],
        "rulebook",
        "a" * 64,
    )


def save(tmp_path, value):
    path = tmp_path / "lexicon.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_draft_is_pending_and_cannot_change_audit_statuses(tmp_path):
    value = draft()
    assert value["review"]["state"] == "pending"
    assert value["entries"][0]["decision"] == "pending"
    path, digest = save(tmp_path, value)
    with pytest.raises(ValueError, match="approval"):
        load_approved_lexicon(path, digest, "a" * 64)


def test_approved_literal_unknown_and_stale_or_conflicting_mapping(tmp_path):
    value = draft()
    value["review"] = dict(
        state="approved", reviewer="human", reviewed_at="2026-11-08T00:00:00+00:00"
    )
    value["entries"][0].update(decision="approved", target="shipping")
    path, digest = save(tmp_path, value)
    mapping = load_approved_lexicon(
        path, digest, "a" * 64, now=datetime(2026, 11, 8, 1, tzinfo=timezone.utc)
    )
    assert mapping["custom"] == "shipping" and "unseen" not in mapping
    with pytest.raises(ValueError):
        load_approved_lexicon(path, "0" * 64, "a" * 64)
    with pytest.raises(ValueError):
        load_approved_lexicon(path, digest, "b" * 64)
    value["entries"][0].update(label="Hoàn thành", target="cancelled")
    path, digest = save(tmp_path, value)
    with pytest.raises(ValueError, match="conflict"):
        load_approved_lexicon(path, digest, "a" * 64)


def test_unknown_decision_stays_unknown_and_pending_entry_never_activates(tmp_path):
    value = draft()
    value["review"] = dict(
        state="approved", reviewer="human", reviewed_at="2026-11-08T00:00:00+00:00"
    )
    path, digest = save(tmp_path, value)
    with pytest.raises(ValueError):
        load_approved_lexicon(path, digest, "a" * 64)
    value["entries"][0].update(decision="unknown", target="unknown")
    path, digest = save(tmp_path, value)
    assert load_approved_lexicon(path, digest, "a" * 64)["custom"] is None


def test_literal_category_proposals_remain_pending_and_ambiguous_labels_unknown():
    value = draft_lexicon(
        [
            dict(
                business_id="synthetic",
                cluster="C1",
                labels={"completed": 1, "ok": 1},
                status_sources=[],
            )
        ],
        "rulebook",
        "a" * 64,
    )
    entries = {e["label"]: e for e in value["entries"]}
    assert entries["completed"]["proposed_target"] == "completed"
    assert entries["ok"]["proposed_target"] == "unknown"
    assert all(
        e["target"] == "unknown" and e["decision"] == "pending"
        for e in entries.values()
    )


def test_source_packet_includes_governing_rulebook_without_status_entries():
    from datamate.domain_lib.semantic_review import source_review_packet

    rulebook = "| Trạng thái đơn | bốn nhóm |\n| Doanh thu một đơn | tiền thuần |\n"
    packet = source_review_packet([], "inventory-sha", rulebook, "a" * 64)
    assert packet["review"]["state"] == "pending"
    assert packet["rulebook_sha256"] == "a" * 64
    assert any("tiền thuần" in s["text"] for s in packet["rulebook_evidence"])
    assert packet["rulebook_evidence"][0]["line_start"] == 1
