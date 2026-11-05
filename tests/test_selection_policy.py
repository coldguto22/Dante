import pytest

from dante.models import ActivityProposal
from dante.selection_policy import NoveltyPolicy


def _proposal(summary):
    return ActivityProposal(summary=summary, rationale=f"It evaluates {summary}.", action_type="reflect")


def test_novelty_policy_prefers_lowest_similarity_then_original_order():
    first = _proposal("first")
    second = _proposal("second")
    third = _proposal("third")
    candidates = [
        (first, "first", 0.4),
        (second, "second", 0.1),
        (third, "third", 0.1),
    ]

    assert NoveltyPolicy().select(candidates, [first, second, third])[0] is second


def test_novelty_policy_rejects_empty_candidates():
    with pytest.raises(ValueError):
        NoveltyPolicy().select([], [])
