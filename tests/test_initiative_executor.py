import pytest

from dante.initiative_executor import InitiativeExecutor
from dante.models import ActivityProposal, InitiativeReflection


class RecordingLLM:
    def __init__(self, result="reflection result"):
        self.result = result
        self.messages = None

    def structured(self, messages, schema):
        self.messages = messages
        self.schema = schema
        return InitiativeReflection(response=self.result)


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
        recent_results=[{"evidence_id": "result:cycle-1", "cycle_id": "cycle-1", "action_type": "reflect", "status": "completed", "result": "Earlier outcome evidence."}],
        recent_selected_summaries=["Earlier selected question."],
        on_prompt=recorded.append,
    )

    assert result.response == "reflection result"
    assert recorded == [llm.messages]
    assert "Dante, an experimental local" in llm.messages[0]["content"]
    assert "Earlier outcome evidence." in llm.messages[1]["content"]
    assert "result:cycle-1" in llm.messages[1]["content"]
    assert llm.schema is InitiativeReflection
    assert "Earlier selected question." in llm.messages[1]["content"]
    assert "no access" in llm.messages[0]["content"]
    assert "Put only the direct answer in response" in llm.messages[0]["content"]
    schema = InitiativeReflection.model_json_schema()
    assert "Direct answer only" in schema["properties"]["response"]["description"]


def test_reflection_executor_rejects_unimplemented_action_types():
    executor = InitiativeExecutor(RecordingLLM())
    proposal = ActivityProposal(summary="Search the web", action_type="research_question")

    with pytest.raises(ValueError, match="No executor"):
        executor.execute(
            proposal,
            recent_results=[],
            recent_selected_summaries=[],
        )


def test_reflection_executor_preserves_evidence_claims_for_audit():
    class ReferencingLLM(RecordingLLM):
        def structured(self, messages, schema):
            self.messages = messages
            return InitiativeReflection(response="Answer", used_evidence_ids=["result:real", "result:invented"])

    executor = InitiativeExecutor(ReferencingLLM())
    report = executor.execute(
        ActivityProposal(summary="Review the earlier outcome", action_type="reflect"),
        recent_results=[{"evidence_id": "result:real", "result": "Observed output"}],
        recent_selected_summaries=[],
    )
    assert report.used_evidence_ids == ["result:real", "result:invented"]
