"""Explicit executor for the bounded local initiative action set."""
from collections.abc import Callable

from dante.llm import OllamaLLM
from dante.models import ActivityProposal, InitiativeReflection


class InitiativeExecutor:
    """Execute only local reflection; all other initiative actions remain proposals."""

    EXECUTABLE_ACTIONS = frozenset({"reflect"})

    def __init__(self, llm: OllamaLLM) -> None:
        self.llm = llm

    def supports(self, action_type: str) -> bool:
        return action_type in self.EXECUTABLE_ACTIONS

    def execute(
        self,
        proposal: ActivityProposal,
        *,
        recent_results: list[dict[str, object]],
        recent_selected_summaries: list[str],
        on_prompt: Callable[[list[dict[str, str]]], None] | None = None,
    ) -> InitiativeReflection:
        """Run one bounded reflection with recent outcomes as explicitly labeled context."""
        if not self.supports(proposal.action_type):
            raise ValueError(f"No executor is registered for {proposal.action_type!r}.")
        history_items = recent_results[-3:]
        history = "\n".join(
            f"- Evidence ID: {item.get('evidence_id', 'unknown')}\n"
            f"  Cycle: {item.get('cycle_id', 'unknown')}\n"
            f"  Action/status: {item.get('action_type', 'unknown')}/"
            f"{item.get('status', 'unknown')}\n"
            f"  Prior model output (unverified): {item.get('result', '')}"
            for item in history_items
        ) or "- No earlier execution results are available."
        selected_history = "\n".join(
            f"- Earlier selected proposal: {summary}"
            for summary in recent_selected_summaries[-5:]
        ) or "- No earlier initiative decisions are available."
        messages = [
            {
                "role": "system",
                "content": (
                    "Perform one bounded internal reflection for Dante, an experimental local "
                    "agent research project. This experiment investigates whether initiative "
                    "cycles produce distinct relevant proposals, execute a permitted local "
                    "reflection, record its outcome, and use that outcome later. The only "
                    "implemented initiative executor is local reflection. Dante has no access "
                    "to web search, arbitrary files, shell commands, or external services. "
                    "Use only the question and the supplied historical outcomes. Return the "
                    "required structured fields. Cite only supplied evidence IDs in "
                    "used_evidence_ids. A proposed check is not an executed check. This call "
                    "performs only a reflection; no local inspection or other check is run. "
                    "Do not claim "
                    "to access tools, files, the web, or external services. Distinguish what "
                    "the evidence says from inference and unknowns. If context is insufficient, "
                    "state what is missing and propose a concrete local check. Keep the result concise."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Reflection question: {proposal.summary}\n"
                    f"Proposal rationale: {proposal.rationale or '(none supplied)'}\n"
                    f"Recent selected proposal summaries:\n{selected_history}\n"
                    f"Prior outcomes (historical model output, not verified facts):\n{history}"
                ),
            },
        ]
        if on_prompt is not None:
            on_prompt(messages)
        result = self.llm.structured(messages, InitiativeReflection)
        report = InitiativeReflection.model_validate(result.model_dump())
        return report
