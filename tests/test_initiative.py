import json

import pytest

from dante.config import Settings
from dante.initiative import InitiativeRunner
from dante.memory import EventStore
from dante.models import ActivityProposal, ActivityProposalBatch


class FakeStructuredLLM:
    def __init__(self, batch):
        self.batch = batch
        self.calls = []

    def structured(self, messages, schema):
        self.calls.append((messages, schema))
        return self.batch


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
