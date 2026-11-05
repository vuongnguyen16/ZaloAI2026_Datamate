import pytest

from datamate.evaluation import paired_bootstrap


def records(scores):
    return [
        dict(
            id=str(i),
            business_id="A" if i < 2 else "B",
            group_id="groupA" if i < 2 else "groupB",
            score=s,
        )
        for i, s in enumerate(scores)
    ]


def test_bootstrap_pairs_clusters_weights_questions_and_is_deterministic():
    candidate, control = records([-1, -1, 1]), records([0, 0, 0])
    result = paired_bootstrap(candidate, control)
    assert result == paired_bootstrap(list(reversed(candidate)), control)
    assert result["delta_pa"] == pytest.approx(-1 / 3)
    assert result["business_id"]["low"] == -1 and result["business_id"]["high"] == 1
    assert result["small_cluster_warning"] and not result["significance_claim_allowed"]
    zero = paired_bootstrap(control, control)
    assert zero["delta_pa"] == zero["group_id"]["low"] == zero["group_id"]["high"] == 0


def test_bootstrap_rejects_unpaired_or_invalid_scores():
    with pytest.raises(ValueError):
        paired_bootstrap(records([1, 0]), records([1]))
    with pytest.raises(ValueError):
        paired_bootstrap(records([True, 0]), records([1, 0]))
    with pytest.raises(ValueError):
        paired_bootstrap(records([1]), records([1]), replicates=999)
