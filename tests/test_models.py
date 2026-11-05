from pydantic import ValidationError
import pytest

from dante.models import ActivityProposal, Message


def test_message_accepts_user_message():
    assert Message(role="user", content="Hello").content == "Hello"


def test_message_rejects_empty_content():
    with pytest.raises(ValidationError):
        Message(role="user", content="")


def test_activity_proposal_requires_rationale():
    with pytest.raises(ValidationError):
        ActivityProposal(summary="Answer the user")
    with pytest.raises(ValidationError):
        ActivityProposal(summary="Answer the user", rationale="")


def test_activity_proposal_rejects_unknown_action():
    with pytest.raises(ValidationError):
        ActivityProposal(summary="Do something", action_type="run_shell")
