import json

from dante.config import Settings
from dante.initiative import InitiativeRunner
from dante.initiative_feedback import InitiativeFeedbackEvaluator
from dante.memory import EventStore
from dante.models import (
    ActivityProposal,
    ActivityProposalBatch,
    AgentEvent,
    InitiativeReflection,
)


def test_deterministic_feedback_flags_invalid_ids_and_duplicated_checks():
    feedback = InitiativeFeedbackEvaluator().evaluate(
        "cycle-2",
        InitiativeReflection(
            response="We should inspect earlier outcomes after identifying the failure.",
            used_evidence_ids=["result:invented"],
            proposed_checks=["inspect earlier outcomes"],
        ),
        available_evidence_ids={"result:cycle-1"},
    )

    checks = {check.check_id: check for check in feedback.checks}
    assert feedback.source == "deterministic_program"
    assert checks["citation_integrity"].status == "fail"
    assert "result:invented" in checks["citation_integrity"].message
    assert checks["exact_check_duplication"].status == "fail"
    assert checks["check_execution_and_progress"].status == "unverified"
    assert any("exact evidence IDs" in guidance for guidance in feedback.guidance)
    assert any("not an executed check" in guidance for guidance in feedback.guidance)


class FakeStructuredLLM:
    def __init__(self, batches):
        self.batches = list(batches)
        self.calls = []

    def structured(self, messages, schema):
        self.calls.append((messages, schema))
        return self.batches.pop(0)


class FeedbackExecutor:
    EXECUTABLE_ACTIONS = frozenset({"reflect"})

    def __init__(self):
        self.calls = []

    def supports(self, action_type):
        return action_type in self.EXECUTABLE_ACTIONS

    def execute(
        self, proposal, *, recent_results, recent_selected_summaries,
        recent_feedback=None, on_prompt=None,
    ):
        self.calls.append(recent_feedback or [])
        if on_prompt:
            on_prompt([{"role": "user", "content": proposal.summary}])
        return InitiativeReflection(
            response="Inspect previous outcomes. Inspect previous outcomes.",
            used_evidence_ids=["invented-id"],
            proposed_checks=["Inspect previous outcomes."],
        )


def test_opt_in_feedback_is_logged_and_injected_into_next_cycle(tmp_path):
    proposal1 = ActivityProposal(summary="Review the first cycle", action_type="reflect")
    proposal2 = ActivityProposal(summary="Correct the citation in the prior reflection", action_type="reflect")
    llm = FakeStructuredLLM([
        ActivityProposalBatch(proposals=[proposal1]),
        ActivityProposalBatch(proposals=[proposal2]),
    ])
    store = EventStore(tmp_path / "feedback.sqlite3")
    executor = FeedbackExecutor()
    runner = InitiativeRunner(
        Settings(db_path=tmp_path / "feedback.sqlite3"),
        llm=llm,
        store=store,
        executor=executor,
    )

    first = runner.cycle(execute=True, external_feedback=True)
    second = runner.cycle(execute=True, external_feedback=True)

    assert first["external_feedback"]["cycle_id"] == first["cycle_id"]
    feedback_events = [event for event in store.recent(limit=30) if event.event_type == "initiative_feedback"]
    assert len(feedback_events) == 2
    stored = json.loads(feedback_events[0].content)
    assert stored["source"] == "deterministic_program"
    assert "invented-id" in stored["checks"][0]["message"]
    proposal_prompt = llm.calls[1][0][0]["content"]
    reflection_feedback = executor.calls[1]
    assert "Prior program-generated feedback" in proposal_prompt
    assert "invented-id" in proposal_prompt
    assert reflection_feedback[0]["cycle_id"] == first["cycle_id"]
    assert "invented-id" in json.dumps(reflection_feedback, ensure_ascii=False)
    assert second["execution"]["progress_verified"] is False


def test_external_feedback_is_rejected_outside_execute_mode(tmp_path):
    llm = FakeStructuredLLM([])
    runner = InitiativeRunner(
        Settings(db_path=tmp_path / "feedback.sqlite3"),
        llm=llm,
        store=EventStore(tmp_path / "feedback.sqlite3"),
    )
    try:
        runner.cycle(external_feedback=True)
    except ValueError as exc:
        assert "execute mode" in str(exc)
    else:
        raise AssertionError("feedback must remain opt-in to execute mode")
    assert llm.calls == []
