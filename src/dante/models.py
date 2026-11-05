"""Structured data models used by the agent and its event log."""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)


class EventLogInspectionRequest(BaseModel):
    """One bounded, code-owned query over an experiment event log."""

    query: Literal[
        "event_counts", "recent_results", "cycle_result", "recent_decisions"
    ]
    limit: int = Field(default=5, ge=1, le=10)
    cycle_id: str | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_query_parameters(self) -> "EventLogInspectionRequest":
        if self.query == "cycle_result" and self.cycle_id is None:
            raise ValueError("cycle_result requires cycle_id")
        if self.query != "cycle_result" and self.cycle_id is not None:
            raise ValueError("cycle_id is only valid for cycle_result")
        return self


class ActivityProposal(BaseModel):
    summary: str = Field(min_length=1, max_length=500)
    rationale: str = Field(min_length=1, max_length=1500)
    action_type: Literal[
        "respond", "reflect", "research_question", "inspect_event_log", "stop"
    ] = "respond"
    requires_external_action: bool = False
    inspection: EventLogInspectionRequest | None = None


class ActivityProposalBatch(BaseModel):
    proposals: list[ActivityProposal] = Field(min_length=1, max_length=3)


class ExecutableActivityProposal(BaseModel):
    """Proposal schema limited to the action types supported by execute mode."""

    summary: str = Field(min_length=1, max_length=500)
    rationale: str = Field(min_length=1, max_length=1500)
    action_type: Literal["reflect", "inspect_event_log", "stop"]
    requires_external_action: bool = False
    inspection: EventLogInspectionRequest | None = None


class ExecutableActivityProposalBatch(BaseModel):
    proposals: list[ExecutableActivityProposal] = Field(min_length=1, max_length=3)


class InitiativeReflection(BaseModel):
    """Structured model response; fields describe claims, not verified progress."""

    response: str = Field(
        min_length=1, max_length=4000,
        description="Direct answer only. Do not put interpretations, missing information, or proposed checks here.",
    )
    used_evidence_ids: list[str] = Field(
        default_factory=list, max_length=10,
        description="IDs of supplied historical outcomes actually used; cite only exact supplied IDs.",
    )
    inferences: list[str] = Field(
        default_factory=list, max_length=10,
        description="Interpretations that go beyond the recorded evidence; state each as an inference.",
    )
    unknowns: list[str] = Field(
        default_factory=list, max_length=10,
        description="Information needed to answer but absent from the supplied context.",
    )
    proposed_checks: list[str] = Field(
        default_factory=list, max_length=5,
        description="Concrete checks that could be run later. These are proposals, never checks already performed.",
    )


class InitiativeFeedbackCheck(BaseModel):
    """One deterministic, program-generated observation about a reflection output."""

    check_id: str = Field(min_length=1, max_length=80)
    status: Literal["pass", "fail", "not_applicable", "unverified"]
    message: str = Field(min_length=1, max_length=1000)


class InitiativeFeedback(BaseModel):
    """Extrinsic feedback from code-owned checks, not a model quality score."""

    cycle_id: str = Field(min_length=1, max_length=100)
    source: Literal["deterministic_program"] = "deterministic_program"
    checks: list[InitiativeFeedbackCheck] = Field(min_length=1, max_length=5)
    guidance: list[str] = Field(default_factory=list, max_length=5)


class AgentEvent(BaseModel):
    timestamp: datetime = Field(default_factory=utc_now)
    event_type: Literal[
        "user_message", "assistant_message", "proposal", "initiative_decision",
        "initiative_prompt", "initiative_result", "initiative_feedback", "error",
        "initiative_check", "initiative_check_result"
    ]
    content: str = Field(min_length=1, max_length=20000)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class UserMemoryRecord(BaseModel):
    """A verbatim user-authored memory excerpt linked to its source event."""

    id: int
    source_event_id: int
    source_event_type: Literal["user_message"]
    source_timestamp: datetime
    created_at: datetime
    session_id: str | None = None
    content: str = Field(min_length=1, max_length=20000)
