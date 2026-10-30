"""Small deterministic feedback checks for initiative reflection experiments."""
import re

from dante.models import InitiativeFeedback, InitiativeFeedbackCheck, InitiativeReflection


class InitiativeFeedbackEvaluator:
    """Check only program-verifiable structure; never score usefulness or progress."""

    VERSION = "deterministic-reflection-feedback-v1"

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text.casefold()).strip()

    def evaluate(
        self,
        cycle_id: str,
        reflection: InitiativeReflection,
        *,
        available_evidence_ids: set[str],
    ) -> InitiativeFeedback:
        cited_ids = reflection.used_evidence_ids
        invalid_ids = [item for item in cited_ids if item not in available_evidence_ids]
        if not cited_ids:
            citation_check = InitiativeFeedbackCheck(
                check_id="citation_integrity",
                status="not_applicable",
                message="The reflection did not cite historical evidence IDs.",
            )
        elif invalid_ids:
            citation_check = InitiativeFeedbackCheck(
                check_id="citation_integrity",
                status="fail",
                message=f"These IDs were not supplied: {', '.join(invalid_ids)}.",
            )
        else:
            citation_check = InitiativeFeedbackCheck(
                check_id="citation_integrity",
                status="pass",
                message="Every cited ID exactly matches a supplied historical outcome.",
            )

        response = self._normalize(reflection.response)
        duplicated_checks = [
            check for check in reflection.proposed_checks
            if len(self._normalize(check)) >= 12
            and self._normalize(check) in response
        ]
        if duplicated_checks:
            separation_check = InitiativeFeedbackCheck(
                check_id="exact_check_duplication",
                status="fail",
                message="At least one proposed check is repeated verbatim in the response field.",
            )
        else:
            separation_check = InitiativeFeedbackCheck(
                check_id="exact_check_duplication",
                status="pass",
                message="No exact proposed-check text was found inside the response field.",
            )

        execution_check = InitiativeFeedbackCheck(
            check_id="check_execution_and_progress",
            status="unverified",
            message=(
                "This executor ran a reflection call only. No proposed check was executed, "
                "so progress remains unverified."
            ),
        )
        guidance: list[str] = []
        if invalid_ids:
            guidance.append(
                "Use only exact evidence IDs supplied in the prompt, or cite no IDs and state the unknown."
            )
        if duplicated_checks:
            guidance.append(
                "Keep the response as a direct answer; put a suggested check only in proposed_checks."
            )
        guidance.append(
            "A proposed check is not an executed check; do not describe it as progress."
        )
        return InitiativeFeedback(
            cycle_id=cycle_id,
            checks=[citation_check, separation_check, execution_check],
            guidance=guidance,
        )
