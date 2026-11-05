"""Code-owned policies for selecting among authorized initiative candidates."""
from collections.abc import Sequence
from typing import Protocol, TypeAlias

from dante.models import ActivityProposal

SelectionCandidate: TypeAlias = tuple[ActivityProposal, str, float]


class SelectionPolicy(Protocol):
    def select(
        self,
        candidates: Sequence[SelectionCandidate],
        proposal_order: Sequence[ActivityProposal],
    ) -> SelectionCandidate:
        """Select one authorized candidate without executing it."""


class NoveltyPolicy:
    """Preserve the initial deterministic novelty baseline exactly."""

    def select(
        self,
        candidates: Sequence[SelectionCandidate],
        proposal_order: Sequence[ActivityProposal],
    ) -> SelectionCandidate:
        if not candidates:
            raise ValueError("At least one candidate is required.")
        return max(
            candidates,
            key=lambda candidate: (
                1.0 - candidate[2],
                -proposal_order.index(candidate[0]),
            ),
        )
