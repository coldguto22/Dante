import pytest

from dante.initiative_executor import InitiativeExecutor
from dante.models import ActivityProposal


class RecordingLLM:
    def __init__(self, result="reflection result"):
        self.result = result
        self.messages = None

    def chat(self, messages):
        self.messages = messages
        return self.result


def test_reflection_executor_uses_bounded_context_and_records_prompt():
    llm = RecordingLLM()
    executor = InitiativeExecutor(llm)
    proposal = ActivityProposal(
        summary="How did the previous result affect this cycle?",
        rationale="Check continuity.",
        action_type="reflect",
    )
    recorded = []

    result = executor.execute(
        proposal,
        recent_results=[{"result": "Earlier outcome evidence."}],
        recent_selected_summaries=["Earlier selected question."],
        on_prompt=recorded.append,
    )

    assert result == "reflection result"
    assert recorded == [llm.messages]
    assert "Dante, an experimental local" in llm.messages[0]["content"]
    assert "Earlier outcome evidence." in llm.messages[1]["content"]
    assert "Earlier selected question." in llm.messages[1]["content"]
    assert "no access" in llm.messages[0]["content"]


def test_reflection_executor_rejects_unimplemented_action_types():
    executor = InitiativeExecutor(RecordingLLM())
    proposal = ActivityProposal(summary="Search the web", action_type="research_question")

    with pytest.raises(ValueError, match="No executor"):
        executor.execute(
            proposal,
            recent_results=[],
            recent_selected_summaries=[],
        )
