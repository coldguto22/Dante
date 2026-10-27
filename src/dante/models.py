"""Structured data models used by the agent and its event log."""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)


class ActivityProposal(BaseModel):
    summary: str = Field(min_length=1, max_length=500)
    rationale: str = Field(default="", max_length=1500)
    action_type: Literal["respond", "reflect", "research_question", "stop"] = "reflect"
    requires_external_action: bool = False


class ActivityProposalBatch(BaseModel):
    proposals: list[ActivityProposal] = Field(min_length=1, max_length=3)


class AgentEvent(BaseModel):
    timestamp: datetime = Field(default_factory=utc_now)
    event_type: Literal[
        "user_message", "assistant_message", "proposal", "initiative_decision", "error"
    ]
    content: str = Field(min_length=1, max_length=20000)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
