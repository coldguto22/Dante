from dante.capabilities import CapabilityRegistry
from dante.models import ActivityProposal, EventLogInspectionRequest


def test_registry_lists_available_planned_restricted_and_unavailable_capabilities():
    registry = CapabilityRegistry()
    statuses = {item.status for item in registry.all()}

    assert {"available", "planned", "restricted", "unavailable"} <= statuses
    assert registry.get("web_research").status == "planned"
    assert registry.get("shell_execution").status == "unavailable"
    assert registry.get("inspect_event_log").external_effects is False


def test_known_internal_proposal_is_authorized_for_dry_run_only():
    registry = CapabilityRegistry()
    proposal = ActivityProposal(
        summary="Review a recent unresolved question",
        rationale="It examines the question.",
        action_type="reflect",
    )

    decision = registry.authorize_proposal(proposal, dry_run=True)

    assert decision.allowed is True
    assert "no action executed" in decision.reason


def test_external_action_request_is_rejected_even_if_action_type_looks_internal():
    registry = CapabilityRegistry()
    proposal = ActivityProposal(
        summary="Search the web for current information",
        rationale="It would gather information.",
        action_type="research_question",
        requires_external_action=True,
    )

    decision = registry.authorize_proposal(proposal, dry_run=True)

    assert decision.allowed is False
    assert "External actions" in decision.reason


def test_registry_alone_does_not_authorize_execution():
    registry = CapabilityRegistry()
    proposal = ActivityProposal(summary="Reflect", rationale="It performs reflection.", action_type="reflect")

    decision = registry.authorize_proposal(proposal, dry_run=False)

    assert decision.allowed is False
    assert "cannot authorize execution" in decision.reason


def test_read_only_inspection_is_a_registered_internal_action():
    proposal = ActivityProposal(
        summary="Inspect the event log",
        rationale="It checks recorded outcomes.",
        action_type="inspect_event_log",
    )
    decision = CapabilityRegistry().authorize_proposal(proposal, dry_run=True)
    assert decision.allowed is False
    assert "validated fixed-query request" in decision.reason

    valid_proposal = proposal.model_copy(update={
        "inspection": EventLogInspectionRequest(query="event_counts")
    })
    valid_decision = CapabilityRegistry().authorize_proposal(valid_proposal, dry_run=True)
    assert valid_decision.allowed is True


def test_inspection_request_cannot_be_attached_to_a_different_action():
    proposal = ActivityProposal(
        summary="Reflect on the experiment",
        rationale="It considers the evidence.",
        action_type="reflect",
        inspection=EventLogInspectionRequest(query="event_counts"),
    )

    decision = CapabilityRegistry().authorize_proposal(proposal, dry_run=True)

    assert decision.allowed is False
    assert "only allowed for inspect_event_log" in decision.reason
