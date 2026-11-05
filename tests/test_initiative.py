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
    EventLogInspectionRequest,
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

    def execute(self, proposal, *, recent_results, recent_selected_summaries, recent_feedback=None, on_prompt=None):
        self.calls.append((proposal, recent_results, recent_feedback or []))
        if on_prompt:
            on_prompt([{"role": "user", "content": proposal.summary}])
        if self.error:
            raise self.error
        return InitiativeReflection(response=self.result)


def test_cycle_records_candidates_and_selected_decision_without_execution(tmp_path):
    batch = ActivityProposalBatch(proposals=[
        ActivityProposal(summary="Review an unresolved question about memory", rationale="It examines memory.", action_type="reflect"),
        ActivityProposal(summary="Formulate a test for retrieval relevance", rationale="It tests retrieval.", action_type="research_question"),
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
    assert "Prior program-generated feedback" not in runner.llm.calls[0][0][0]["content"]
    assert all(event.event_type != "initiative_feedback" for event in events)


def test_cycle_rejects_candidates_that_request_external_actions(tmp_path):
    batch = ActivityProposalBatch(proposals=[
        ActivityProposal(
            summary="Search the web for recent papers",
            rationale="It would investigate the topic.",
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
        ActivityProposal(summary="Stop this experiment cycle", rationale="It ends the bounded run.", action_type="stop"),
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
    proposal = ActivityProposal(summary="Stop this initiative", rationale="It ends the run.", action_type="stop")
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
    proposal = ActivityProposal(summary="Review the unresolved memory question", rationale="It examines memory.", action_type="reflect")
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


def test_execute_mode_runs_read_only_event_log_check_and_keeps_progress_unverified(tmp_path):
    proposal = ActivityProposal(
        summary="Inspect recorded event counts",
        rationale="It checks what the experiment has recorded.",
        action_type="inspect_event_log",
        inspection=EventLogInspectionRequest(query="event_counts"),
    )
    database = tmp_path / "initiative-experiment.sqlite3"
    store = EventStore(database)
    runner = InitiativeRunner(
        Settings(db_path=database),
        llm=FakeStructuredLLM(ActivityProposalBatch(proposals=[proposal])),
        store=store,
    )

    result = runner.cycle(execute=True)

    assert result["execution"]["status"] == "completed"
    assert result["execution"]["check_was_actually_run"] is True
    assert result["execution"]["progress_verified"] is False
    events = store.recent(limit=20)
    assert any(event.event_type == "initiative_check" for event in events)
    check_result = next(event for event in events if event.event_type == "initiative_check_result")
    assert json.loads(check_result.content)["status"] == "completed"


def test_reflection_only_dry_run_uses_execution_schema_without_executing(tmp_path):
    proposal = ActivityProposal(summary="Reflect on the bounded experiment", rationale="It examines the experiment.", action_type="reflect")
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
    proposal = ActivityProposal(summary="Reflect on retrieval quality", rationale="It checks retrieval.", action_type="reflect")
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
        def execute(self, proposal, *, recent_results, recent_selected_summaries, recent_feedback=None, on_prompt=None):
            return InitiativeReflection(response="Claim", used_evidence_ids=["result:invented"])

    proposal = ActivityProposal(summary="Review context", rationale="It reviews context.", action_type="reflect")
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
    proposal = ActivityProposal(summary="Formulate a research question", rationale="It frames a test.", action_type="research_question")
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
    first = ActivityProposal(summary="Inspect memory retrieval limits", rationale="It inspects limits.", action_type="reflect")
    second = ActivityProposal(summary="Assess the unresolved retrieval issue", rationale="It assesses the issue.", action_type="reflect")
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
    duplicate = ActivityProposal(summary="Review the memory retrieval limitations", rationale="It revisits limits.", action_type="reflect")
    distinct = ActivityProposal(summary="Check whether outcomes influence later selections", rationale="It tests influence.", action_type="reflect")
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
    repeated = ActivityProposal(summary="Review the same retrieval question", rationale="It repeats the question.", action_type="reflect")
    distinct = ActivityProposal(summary="Measure outcome use in the next cycle", rationale="It measures outcome use.", action_type="reflect")
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


def test_distilled_history_hides_model_text_and_records_state_facts(tmp_path):
    class DistilledExecutor(FakeExecutor):
        def execute(
            self, proposal, *, recent_results, recent_selected_summaries,
            recent_feedback=None, history_mode="raw", state_facts=None, on_prompt=None,
        ):
            self.distilled_prompt = (history_mode, state_facts, recent_results)
            if on_prompt:
                on_prompt([{"role": "user", "content": proposal.summary}])
            return InitiativeReflection(response="bounded result")

    proposal = ActivityProposal(
        summary="Review the prior result",
        rationale="It checks continuity.",
        action_type="reflect",
    )
    proposal2 = ActivityProposal(
        summary="Measure the next bounded outcome",
        rationale="It compares the next cycle.",
        action_type="reflect",
    )
    llm = FakeStructuredLLM([
        ActivityProposalBatch(proposals=[proposal]),
        ActivityProposalBatch(proposals=[proposal2]),
    ])
    store = EventStore(tmp_path / "distilled.sqlite3")
    executor = DistilledExecutor("UNIQUE-SENTINEL")
    runner = InitiativeRunner(
        Settings(db_path=tmp_path / "distilled.sqlite3"),
        llm=llm,
        store=store,
        executor=executor,
    )
    runner.cycle(execute=True, history_mode="raw")
    runner.cycle(execute=True, history_mode="distilled")

    proposal_prompt = llm.calls[1][0][0]["content"]
    assert "UNIQUE-SENTINEL" not in proposal_prompt
    assert executor.distilled_prompt[0] == "distilled"
    assert executor.distilled_prompt[1]["prior_results"] == 1
    assert executor.distilled_prompt[1]["prior_selected_summaries"] == 1
    assert "UNIQUE-SENTINEL" not in json.dumps(executor.distilled_prompt[2])
    prompt_events = [
        event for event in store.recent(limit=100)
        if event.event_type == "initiative_prompt"
    ]
    assert all(event.metadata["history_mode"] == "raw" for event in prompt_events[:2])
    assert all(event.metadata["history_mode"] == "distilled" for event in prompt_events[2:])


def test_execution_proposal_schema_excludes_unsupported_actions():
    with pytest.raises(ValueError):
        ExecutableActivityProposalBatch(proposals=[
            ExecutableActivityProposal(summary="Respond to a user", rationale="It answers the user.", action_type="respond")
        ])
