from pydantic import ValidationError
import pytest

from dante.models import ActivityProposal, Message


def test_message_accepts_user_message():
    assert Message(role="user", content="Hello").content == "Hello"


def test_message_rejects_empty_content():
    with pytest.raises(ValidationError):
        Message(role="user", content="")


def test_activity_proposal_defaults_to_response():
    proposal = ActivityProposal(summary="Answer the user")
    assert proposal.action_type == "respond"
    assert proposal.requires_external_action is False


def test_activity_proposal_rejects_unknown_action():
    with pytest.raises(ValidationError):
        ActivityProposal(summary="Do something", action_type="run_shell")
