"""Bounded, inspectable initiative cycle. All cycles are dry-run only."""
import argparse
import json
import uuid
from collections.abc import Sequence

from dante.capabilities import CapabilityRegistry
from dante.config import Settings, get_settings
from dante.llm import OllamaLLM
from dante.memory import EventStore
from dante.models import ActivityProposal, ActivityProposalBatch, AgentEvent


class InitiativeRunner:
    """Generate a small proposal batch, authorize it, select one, and log the result."""

    def __init__(
        self,
        settings: Settings,
        llm: OllamaLLM | None = None,
        store: EventStore | None = None,
        registry: CapabilityRegistry | None = None,
    ) -> None:
        self.settings = settings
        self.llm = llm or OllamaLLM(settings)
        self.store = store or EventStore(settings.db_path)
        self.registry = registry or CapabilityRegistry()

    @staticmethod
    def _similarity(left: str, right: str) -> float:
        left_tokens = {token.casefold() for token in left.split() if len(token) > 2}
        right_tokens = {token.casefold() for token in right.split() if len(token) > 2}
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)

    def _recent_selected_summaries(self, limit: int = 5) -> list[str]:
        summaries: list[str] = []
        for event in reversed(self.store.recent(limit=100)):
            if event.event_type != "initiative_decision":
                continue
            try:
                payload = json.loads(event.content)
            except (TypeError, json.JSONDecodeError):
                continue
            if payload.get("decision") == "selected" and isinstance(payload.get("summary"), str):
                summaries.append(payload["summary"])
                if len(summaries) >= limit:
                    break
        return summaries

    def cycle(self) -> dict[str, object]:
        cycle_id = uuid.uuid4().hex
        recent_summaries = self._recent_selected_summaries()
        registry_context = [
            {
                "name": capability.name,
                "status": capability.status,
                "description": capability.description,
                "supported_action_types": list(capability.supported_action_types),
                "external_effects": capability.external_effects,
            }
            for capability in self.registry.all()
        ]
        prompt = (
            "You are generating candidate activities for Dante's bounded local initiative experiment. "
            "Return 1 to 3 distinct, small proposals in the required schema. Only propose internal "
            "reflection, formulating a question, a conversational response, or stopping this cycle. "
            "Do not claim to have used tools. Do not request web, filesystem, shell, or external-service "
            "actions. Set requires_external_action=false only when the proposal truly needs no external "
            "action. Prefer a concrete useful question over vague self-description. Avoid repeating "
            "recent selected summaries when possible. These are proposals, not actions being executed.\n"
            f"Registered capabilities: {json.dumps(registry_context, ensure_ascii=False)}\n"
            f"Recent selected summaries: {json.dumps(recent_summaries, ensure_ascii=False)}"
        )
        batch = self.llm.structured(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Propose the next bounded initiative candidates."},
            ],
            ActivityProposalBatch,
        )
        if not isinstance(batch, ActivityProposalBatch):
            batch = ActivityProposalBatch.model_validate(batch.model_dump())

        candidates: list[tuple[ActivityProposal, str, float]] = []
        for index, proposal in enumerate(batch.proposals, start=1):
            authorization = self.registry.authorize_proposal(proposal, dry_run=True)
            similarity = max(
                (self._similarity(proposal.summary, previous) for previous in recent_summaries),
                default=0.0,
            )
            self.store.add(AgentEvent(
                event_type="proposal",
                content=proposal.model_dump_json(),
                metadata={
                    "cycle_id": cycle_id,
                    "candidate_index": index,
                    "action_type": proposal.action_type,
                    "capability": authorization.capability_name,
                    "authorized": authorization.allowed,
                    "reason": authorization.reason,
                },
            ))
            if authorization.allowed:
                candidates.append((proposal, authorization.reason, similarity))

        selected: ActivityProposal | None = None
        selected_reason = "No candidate passed capability authorization."
        if candidates:
            selected, _, _ = max(candidates, key=lambda candidate: 1.0 - candidate[2])
            selected_reason = (
                "Selected by the deterministic novelty baseline; "
                "this is a proposal only and has not been executed."
            )
            decision = {
                "cycle_id": cycle_id,
                "decision": "selected",
                "summary": selected.summary,
                "action_type": selected.action_type,
                "reason": selected_reason,
                "execution": "none_dry_run",
            }
        else:
            decision = {
                "cycle_id": cycle_id,
                "decision": "none",
                "summary": None,
                "action_type": None,
                "reason": selected_reason,
                "execution": "none_dry_run",
            }

        self.store.add(AgentEvent(
            event_type="initiative_decision",
            content=json.dumps(decision, ensure_ascii=False),
            metadata={
                "cycle_id": cycle_id,
                "decision": str(decision["decision"]),
                "action_type": selected.action_type if selected else None,
                "execution": "none_dry_run",
            },
        ))
        return {
            "cycle_id": cycle_id,
            "proposals": batch.proposals,
            "selected": selected,
            "reason": selected_reason,
        }

    def run(self, cycles: int = 1) -> list[dict[str, object]]:
        """Run at most ten dry-run cycles; a selected stop proposal ends the loop."""
        if not 1 <= cycles <= 10:
            raise ValueError("cycles must be between 1 and 10")
        results: list[dict[str, object]] = []
        for _ in range(cycles):
            result = self.cycle()
            results.append(result)
            selected = result["selected"]
            if isinstance(selected, ActivityProposal) and selected.action_type == "stop":
                break
        return results


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run Dante's bounded initiative prototype (dry-run; no actions executed)."
    )
    parser.add_argument(
        "--cycles", type=int, default=1,
        help="Number of cycles to simulate (1-10; default: 1).",
    )
    args = parser.parse_args(argv)
    settings = get_settings()
    runner = InitiativeRunner(settings)
    try:
        results = runner.run(args.cycles)
    except ValueError as exc:
        parser.error(str(exc))
    for index, result in enumerate(results, start=1):
        selected = result["selected"]
        print(f"\nCycle {index} ({result['cycle_id']})")
        for proposal_index, proposal in enumerate(result["proposals"], start=1):
            print(f"  Candidate {proposal_index}: [{proposal.action_type}] {proposal.summary}")
        if isinstance(selected, ActivityProposal):
            print(f"  Selected: [{selected.action_type}] {selected.summary}")
        else:
            print("  Selected: none (all candidates were rejected)")
        print(f"  Reason: {result['reason']}")
        print("  Execution: none (dry-run)")
    print(f"\nRecorded results in: {settings.db_path}")


if __name__ == "__main__":
    main()
