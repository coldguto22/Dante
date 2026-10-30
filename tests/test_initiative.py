import json

import pytest

from dante.config import Settings
from dante.initiative import InitiativeRunner
from dante.memory import EventStore
from dante.models import (
    ActivityProposal,
    ActivityProposalBatch,
    AgentEvent,
    ExecutableActivityProposal,
    ExecutableActivityProposalBatch,
    InitiativeReflection,
)


class FakeStructuredLLM:
    def __init__(self, batch):
        self.batch = batch
        self.calls = []

    def structured(self, messages, schema):
        self.calls.append((messages, schema))
        if isinstance(self.batch, list):
            return self.batch.pop(0)
        return self.batch


class FakeExecutor:
    def __init__(self, result="reflection result", error=None):
        self.result = result
        self.error = error
        self.calls = []

    def supports(self, action_type):
        return action_type == "reflect"

    def execute(self, proposal, *, recent_results, recent_selected_summaries, on_prompt=None):
        self.calls.append((proposal, recent_results))
        if on_prompt:
            on_prompt([{"role": "user", "content": proposal.summary}])
        if self.error:
            raise self.error
        return InitiativeReflection(response=self.result)


def test_cycle_records_candidates_and_selected_decision_without_execution(tmp_path):
    batch = ActivityProposalBatch(proposals=[
        ActivityProposal(summary="Review an unresolved question about memory", action_type="reflect"),
        ActivityProposal(summary="Formulate a test for retrieval relevance", action_type="research_question"),
    ])
    store = EventStore(tmp_path / "initiative.sqlite3")
    runner = InitiativeRunner(
        Settings(db_path=tmp_path / "initiative.sqlite3"),
        llm=FakeStructuredLLM(batch),
        store=store,
    )

    result = runner.cycle()
    events = store.recent(limit=10)
    proposal_events = [event for event in events if event.event_type == "proposal"]
    decisions = [event for event in events if event.event_type == "initiative_decision"]

    assert len(proposal_events) == 2
    assert len(decisions) == 1
    assert result["selected"] in batch.proposals
    assert json.loads(decisions[0].content)["execution"] == "none_dry_run"
    assert decisions[0].metadata["execution"] == "none_dry_run"
    assert runner.llm.calls[0][1] is ActivityProposalBatch


def test_cycle_rejects_candidates_that_request_external_actions(tmp_path):
    batch = ActivityProposalBatch(proposals=[
        ActivityProposal(
            summary="Search the web for recent papers",
            action_type="research_question",
            requires_external_action=True,
        ),
    ])
    store = EventStore(tmp_path / "initiative.sqlite3")
    runner = InitiativeRunner(
        Settings(db_path=tmp_path / "initiative.sqlite3"),
        llm=FakeStructuredLLM(batch),
        store=store,
    )

    result = runner.cycle()

    assert result["selected"] is None
    decision = store.recent(limit=1)[0]
    assert decision.event_type == "initiative_decision"
    assert json.loads(decision.content)["decision"] == "none"


def test_run_bounds_cycles_and_stops_when_stop_proposal_selected(tmp_path):
    batch = ActivityProposalBatch(proposals=[
        ActivityProposal(summary="Stop this experiment cycle", action_type="stop"),
    ])
    runner = InitiativeRunner(
        Settings(db_path=tmp_path / "initiative.sqlite3"),
        llm=FakeStructuredLLM(batch),
        store=EventStore(tmp_path / "initiative.sqlite3"),
    )

    assert len(runner.run(10)) == 1
    with pytest.raises(ValueError):
        runner.run(11)


def test_execute_mode_stop_proposal_ends_without_running_reflection(tmp_path):
    proposal = ActivityProposal(summary="Stop this initiative", action_type="stop")
    store = EventStore(tmp_path / "initiative.sqlite3")
    executor = FakeExecutor()
    runner = InitiativeRunner(
        Settings(db_path=tmp_path / "initiative.sqlite3"),
        llm=FakeStructuredLLM(ActivityProposalBatch(proposals=[proposal])),
        store=store,
        executor=executor,
    )

    results = runner.run(3, execute=True)

    assert len(results) == 1
    assert results[0]["execution"] is None
    assert executor.calls == []
    assert json.loads(store.recent(limit=1)[0].content)["execution"] == "not_applicable_stop"


def test_execute_mode_runs_only_reflection_and_records_result(tmp_path):
    proposal = ActivityProposal(summary="Review the unresolved memory question", action_type="reflect")
    llm = FakeStructuredLLM(ActivityProposalBatch(proposals=[proposal]))
    store = EventStore(tmp_path / "initiative.sqlite3")
    executor = FakeExecutor("Observed limitation: retrieval is lexical.")
    runner = InitiativeRunner(
        Settings(db_path=tmp_path / "initiative.sqlite3"), llm=llm, store=store, executor=executor
    )

    result = runner.cycle(execute=True)

    assert result["execution"]["status"] == "completed"
    assert result["execution"]["result"]["response"] == "Observed limitation: retrieval is lexical."
    assert result["execution"]["action_performed"] is True
    assert result["execution"]["response_status"] == "received"
    assert result["execution"]["progress_verified"] is False
    events = store.recent(limit=10)
    outcome = next(event for event in events if event.event_type == "initiative_result")
    decision = next(event for event in events if event.event_type == "initiative_decision")
    prompts = [event for event in events if event.event_type == "initiative_prompt"]
    assert json.loads(outcome.content)["cycle_id"] == result["cycle_id"]
    assert json.loads(decision.content)["execution"] == "completed"
    assert len(executor.calls) == 1
    assert llm.calls[0][1] is ExecutableActivityProposalBatch
    assert len(prompts) == 2
    assert {event.metadata["phase"] for event in prompts} == {
        "proposal_generation", "reflection_execution"
    }
    assert all(event.metadata["model"] == "llama3.2" for event in prompts)


def test_reflection_only_dry_run_uses_execution_schema_without_executing(tmp_path):
    proposal = ActivityProposal(summary="Reflect on the bounded experiment", action_type="reflect")
    store = EventStore(tmp_path / "initiative.sqlite3")
    executor = FakeExecutor()
    llm = FakeStructuredLLM(ActivityProposalBatch(proposals=[proposal]))
    runner = InitiativeRunner(
        Settings(db_path=tmp_path / "initiative.sqlite3"), llm=llm, store=store, executor=executor
    )

    result = runner.cycle(restrict_to_executable=True)

    assert result["selected"] == proposal
    assert result["execution"] is None
    assert llm.calls[0][1] is ExecutableActivityProposalBatch
    assert executor.calls == []
    assert json.loads(store.recent(limit=1)[0].content)["execution"] == "none_dry_run"


def test_execute_mode_records_executor_errors_without_aborting_cycle(tmp_path):
    proposal = ActivityProposal(summary="Reflect on retrieval quality", action_type="reflect")
    store = EventStore(tmp_path / "initiative.sqlite3")
    runner = InitiativeRunner(
        Settings(db_path=tmp_path / "initiative.sqlite3"),
        llm=FakeStructuredLLM(ActivityProposalBatch(proposals=[proposal])),
        store=store,
        executor=FakeExecutor(error=RuntimeError("model unavailable")),
    )

    result = runner.cycle(execute=True)

    assert result["execution"]["status"] == "error"
    assert "model unavailable" in result["execution"]["result"]
    assert json.loads(store.recent(limit=1)[0].content)["execution"] == "error"


def test_execution_records_invalid_model_evidence_ids_separately(tmp_path):
    class CitingExecutor(FakeExecutor):
        def execute(self, proposal, *, recent_results, recent_selected_summaries, on_prompt=None):
            return InitiativeReflection(response="Claim", used_evidence_ids=["result:invented"])

    proposal = ActivityProposal(summary="Review context", action_type="reflect")
    runner = InitiativeRunner(
        Settings(db_path=tmp_path / "initiative.sqlite3"),
        llm=FakeStructuredLLM(ActivityProposalBatch(proposals=[proposal])),
        store=EventStore(tmp_path / "initiative.sqlite3"),
        executor=CitingExecutor(),
    )
    result = runner.cycle(execute=True)
    assert result["execution"]["evidence_validation"] == {
        "valid_ids": [], "rejected_ids": ["result:invented"]
    }


def test_execute_mode_does_not_run_actions_without_an_executor(tmp_path):
    proposal = ActivityProposal(summary="Formulate a research question", action_type="research_question")
    store = EventStore(tmp_path / "initiative.sqlite3")
    runner = InitiativeRunner(
        Settings(db_path=tmp_path / "initiative.sqlite3"),
        llm=FakeStructuredLLM(ActivityProposalBatch(proposals=[proposal])),
        store=store,
        executor=FakeExecutor(),
    )

    result = runner.cycle(execute=True)

    assert result["selected"] is None
    assert store.recent(limit=1)[0].metadata["execution"] == "no_executable_candidate"


def test_previous_execution_results_are_supplied_to_later_proposals(tmp_path):
    first = ActivityProposal(summary="Inspect memory retrieval limits", action_type="reflect")
    second = ActivityProposal(summary="Assess the unresolved retrieval issue", action_type="reflect")
    llm = FakeStructuredLLM([
        ActivityProposalBatch(proposals=[first]),
        ActivityProposalBatch(proposals=[second]),
    ])
    store = EventStore(tmp_path / "initiative.sqlite3")
    executor = FakeExecutor("The retrieval is lexical.")
    runner = InitiativeRunner(
        Settings(db_path=tmp_path / "initiative.sqlite3"), llm=llm, store=store, executor=executor
    )

    runner.cycle(execute=True)
    runner.cycle(execute=True)

    assert "The retrieval is lexical." in llm.calls[1][0][0]["content"]
    assert '"response": "The retrieval is lexical."' in executor.calls[1][1][0]["result"]


def test_duplicate_candidates_in_same_batch_are_rejected(tmp_path):
    duplicate = ActivityProposal(summary="Review the memory retrieval limitations", action_type="reflect")
    distinct = ActivityProposal(summary="Check whether outcomes influence later selections", action_type="reflect")
    store = EventStore(tmp_path / "initiative.sqlite3")
    store.add(AgentEvent(
        event_type="initiative_decision",
        content=json.dumps({"decision": "selected", "summary": duplicate.summary}),
    ))
    runner = InitiativeRunner(
        Settings(db_path=tmp_path / "initiative.sqlite3"),
        llm=FakeStructuredLLM(ActivityProposalBatch(proposals=[duplicate, duplicate, distinct])),
        store=store,
    )

    result = runner.cycle()

    assert result["selected"] == distinct
    proposal_events = [event for event in store.recent(limit=10) if event.event_type == "proposal"]
    assert proposal_events[0].metadata["authorized"] is True
    assert proposal_events[1].metadata["authorized"] is False
    assert "duplicates" in proposal_events[1].metadata["reason"]


def test_reflection_only_mode_rejects_candidates_matching_recent_selections(tmp_path):
    repeated = ActivityProposal(summary="Review the same retrieval question", action_type="reflect")
    distinct = ActivityProposal(summary="Measure outcome use in the next cycle", action_type="reflect")
    store = EventStore(tmp_path / "initiative.sqlite3")
    store.add(AgentEvent(
        event_type="initiative_decision",
        content=json.dumps({"decision": "selected", "summary": repeated.summary}),
    ))
    runner = InitiativeRunner(
        Settings(db_path=tmp_path / "initiative.sqlite3"),
        llm=FakeStructuredLLM(ActivityProposalBatch(proposals=[repeated, distinct])),
        store=store,
        executor=FakeExecutor(),
    )

    result = runner.cycle(restrict_to_executable=True)

    assert result["selected"] == distinct
    proposal_events = [event for event in store.recent(limit=10) if event.event_type == "proposal"]
    assert proposal_events[0].metadata["authorized"] is False
    assert "recent selected" in proposal_events[0].metadata["reason"]


def test_execution_proposal_schema_excludes_unsupported_actions():
    with pytest.raises(ValueError):
        ExecutableActivityProposalBatch(proposals=[
            ExecutableActivityProposal(summary="Respond to a user", action_type="respond")
        ])
