from dante.capabilities import CapabilityRegistry
from dante.models import ActivityProposal


def test_registry_lists_available_planned_restricted_and_unavailable_capabilities():
    registry = CapabilityRegistry()
    statuses = {item.status for item in registry.all()}

    assert {"available", "planned", "restricted", "unavailable"} <= statuses
    assert registry.get("web_research").status == "planned"
    assert registry.get("shell_execution").status == "unavailable"


def test_known_internal_proposal_is_authorized_for_dry_run_only():
    registry = CapabilityRegistry()
    proposal = ActivityProposal(
        summary="Review a recent unresolved question",
        action_type="reflect",
    )

    decision = registry.authorize_proposal(proposal, dry_run=True)

    assert decision.allowed is True
    assert "no action executed" in decision.reason


def test_external_action_request_is_rejected_even_if_action_type_looks_internal():
    registry = CapabilityRegistry()
    proposal = ActivityProposal(
        summary="Search the web for current information",
        action_type="research_question",
        requires_external_action=True,
    )

    decision = registry.authorize_proposal(proposal, dry_run=True)

    assert decision.allowed is False
    assert "External actions" in decision.reason


def test_execution_mode_is_rejected_because_no_executor_exists():
    registry = CapabilityRegistry()
    proposal = ActivityProposal(summary="Reflect", action_type="reflect")

    decision = registry.authorize_proposal(proposal, dry_run=False)

    assert decision.allowed is False
    assert "not implemented" in decision.reason
