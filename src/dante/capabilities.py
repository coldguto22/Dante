"""Code-owned capability registry and deterministic proposal authorization.

Model output cannot add capabilities or grant itself permission. This registry decides
whether a proposal may be considered; the separate executor independently decides
whether an action type has an implemented execution path.
"""
from typing import Literal

from pydantic import BaseModel, Field

from dante.models import ActivityProposal

CapabilityStatus = Literal["available", "unavailable", "planned", "restricted"]


class Capability(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    status: CapabilityStatus
    supported_action_types: tuple[str, ...] = ()
    external_effects: bool = False
    notes: str = ""


class AuthorizationDecision(BaseModel):
    allowed: bool
    capability_name: str | None = None
    reason: str


class CapabilityRegistry:
    """Immutable-by-convention registry defined by application code."""

    def __init__(self) -> None:
        self._capabilities = (
            Capability(
                name="conversation_response",
                description="Generate a conversational response using the configured local model.",
                status="available",
                supported_action_types=("respond",),
                notes="Available in the interactive conversation path; initiative execution is handled separately.",
            ),
            Capability(
                name="reflection",
                description="Run a bounded local-model reflection; no external action is performed.",
                status="available",
                supported_action_types=("reflect",),
            ),
            Capability(
                name="question_formulation",
                description="Formulate an open question for a later experiment or investigation.",
                status="available",
                supported_action_types=("research_question",),
                notes="Formulating a question is not the same as searching the web or verifying facts.",
            ),
            Capability(
                name="stop_cycle",
                description="End the current initiative loop without performing an action.",
                status="available",
                supported_action_types=("stop",),
            ),
            Capability(
                name="web_research",
                description="Search and verify current information on the public web.",
                status="planned",
                external_effects=True,
                notes="No web-search executor is connected to Dante's local initiative loop.",
            ),
            Capability(
                name="filesystem_read",
                description="Read arbitrary files from the host filesystem.",
                status="restricted",
                external_effects=True,
                notes="No filesystem tool is exposed to the initiative loop.",
            ),
            Capability(
                name="shell_execution",
                description="Run operating-system commands or programs.",
                status="unavailable",
                external_effects=True,
                notes="No shell executor is implemented or exposed.",
            ),
            Capability(
                name="external_write",
                description="Write to external services or modify external resources.",
                status="unavailable",
                external_effects=True,
                notes="No external-write executor is implemented or exposed.",
            ),
        )
        self._by_name = {item.name: item for item in self._capabilities}
        self._by_action = {
            action_type: item
            for item in self._capabilities
            for action_type in item.supported_action_types
        }

    def all(self) -> tuple[Capability, ...]:
        """Return the capabilities in stable display order."""
        return self._capabilities

    def get(self, name: str) -> Capability | None:
        return self._by_name.get(name)

    def authorize_proposal(
        self, proposal: ActivityProposal, *, dry_run: bool = True
    ) -> AuthorizationDecision:
        """Authorize only known, available, non-external proposal types.

        allowed means only that the proposal may be recorded and considered. It does
        not establish that an executor exists or that an action was performed.
        """
        capability = self._by_action.get(proposal.action_type)
        if capability is None:
            return AuthorizationDecision(
                allowed=False, reason="No registered capability supports this action type."
            )
        if capability.status != "available":
            return AuthorizationDecision(
                allowed=False,
                capability_name=capability.name,
                reason=f"Capability status is {capability.status}, not available.",
            )
        if proposal.requires_external_action or capability.external_effects:
            return AuthorizationDecision(
                allowed=False,
                capability_name=capability.name,
                reason="External actions are not permitted in the initiative prototype.",
            )
        if not dry_run:
            return AuthorizationDecision(
                allowed=False,
                capability_name=capability.name,
                reason="The capability registry cannot authorize execution without an executor check.",
            )
        return AuthorizationDecision(
            allowed=True,
            capability_name=capability.name,
            reason="Allowed for proposal recording and selection only; no action executed.",
        )
