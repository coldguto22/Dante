"""Explicit executor for the bounded local initiative action set."""
from collections.abc import Callable

from dante.llm import OllamaLLM
from dante.models import ActivityProposal


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
    ) -> str:
        """Run one bounded reflection with recent outcomes as explicitly labeled context."""
        if not self.supports(proposal.action_type):
            raise ValueError(f"No executor is registered for {proposal.action_type!r}.")
        history = "\n".join(
            f"- Earlier result: {item.get('result', '')}"
            for item in recent_results[-3:]
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
                    "Use only the question and the supplied historical outcomes. Do not claim "
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
        result = self.llm.chat(messages)
        return result[:8000]
