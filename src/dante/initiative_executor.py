"""Explicit executor for the bounded local initiative action set."""
import json
from collections.abc import Callable
from typing import Literal

from dante.llm import OllamaLLM
from dante.models import ActivityProposal, InitiativeReflection


class InitiativeExecutor:
    """Execute only local reflection; all other initiative actions remain proposals."""

    EXECUTABLE_ACTIONS = frozenset({"reflect", "inspect_event_log"})

    def __init__(self, llm: OllamaLLM, reflection_temperature: float | None = None) -> None:
        self.llm = llm
        self.reflection_temperature = reflection_temperature

    def supports(self, action_type: str) -> bool:
        return action_type in self.EXECUTABLE_ACTIONS

    def execute(
        self,
        proposal: ActivityProposal,
        *,
        recent_results: list[dict[str, object]],
        recent_selected_summaries: list[str],
        recent_feedback: list[dict[str, object]] | None = None,
        history_mode: Literal["raw", "distilled"] = "raw",
        state_facts: dict[str, int] | None = None,
        on_prompt: Callable[[list[dict[str, str]]], None] | None = None,
    ) -> InitiativeReflection:
        """Run one bounded reflection with recent outcomes as explicitly labeled context."""
        if not self.supports(proposal.action_type):
            raise ValueError(f"No executor is registered for {proposal.action_type!r}.")
        if proposal.action_type == "inspect_event_log":
            raise ValueError("Event-log inspection is executed by the code-owned inspector.")
        if history_mode not in {"raw", "distilled"}:
            raise ValueError(f"Unknown initiative history mode: {history_mode!r}.")
        history_items = recent_results[-3:]
        history = "\n".join(
            f"- Evidence ID: {item.get('evidence_id', 'unknown')}\n"
            f"  Cycle: {item.get('cycle_id', 'unknown')}\n"
            f"  Action/status: {item.get('action_type', 'unknown')}/"
            f"{item.get('status', 'unknown')}\n"
            + (
                f"  Prior model output (unverified): {item.get('result', '')}"
                if history_mode == "raw"
                else (
                    f"  Selected summary: {item.get('summary', '')}\n"
                    f"  Evidence validation: {item.get('evidence_validation', {})}\n"
                    f"  Progress verified: {item.get('progress_verified', False)}"
                )
            )
            for item in history_items
        ) or "- No earlier execution results are available."
        selected_history = "\n".join(
            f"- Earlier selected proposal: {summary}"
            for summary in recent_selected_summaries[-5:]
        ) or "- No earlier initiative decisions are available."
        feedback_history = "\n".join(
            f"- {json.dumps(item, ensure_ascii=False)}"
            for item in (recent_feedback or [])[-3:]
        )
        if recent_feedback is not None and not feedback_history:
            feedback_history = "- No earlier program-generated feedback is available."
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
                    "Put only the direct answer in response. Put interpretations in inferences, "
                    "missing information in unknowns, and concrete future checks in "
                    "proposed_checks; do not duplicate those items in response. The supplied "
                    "history is a bounded sample: its absence does not establish that the "
                    "database or system has no history. Do not infer runtime state beyond the "
                    "supplied records. Do not claim "
                    "to access tools, files, the web, or external services. Distinguish what "
                    "the evidence says from inference and unknowns. If context is insufficient, "
                    "state what is missing and propose a concrete local check. Keep the result concise. "
                    "Program feedback, if supplied, comes from deterministic code checks; it covers "
                    "only citation IDs, exact field duplication, and whether a check actually ran. "
                    "It is not a score of answer usefulness or general correctness."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Reflection question: {proposal.summary}\n"
                    f"Proposal rationale: {proposal.rationale or '(none supplied)'}\n"
                    + (
                        f"Authoritative program facts: {json.dumps(state_facts, ensure_ascii=False)}\n"
                        if history_mode == "distilled" and state_facts is not None else ""
                    )
                    +
                    f"Recent selected proposal summaries:\n{selected_history}\n"
                    f"Prior outcomes (historical model output, not verified facts):\n{history}"
                    + (
                        "\nPrior program-generated feedback (limited structural checks):\n"
                        f"{feedback_history}"
                        if recent_feedback is not None else ""
                    )
                ),
            },
        ]
        if on_prompt is not None:
            on_prompt(messages)
        previous_temperature = getattr(self.llm, "reflection_temperature", None)
        if hasattr(self.llm, "reflection_temperature"):
            self.llm.reflection_temperature = self.reflection_temperature
        try:
            result = self.llm.structured(messages, InitiativeReflection)
        finally:
            if hasattr(self.llm, "reflection_temperature"):
                self.llm.reflection_temperature = previous_temperature
        report = InitiativeReflection.model_validate(result.model_dump())
        return report
