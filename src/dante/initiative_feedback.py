"""Small deterministic feedback checks for initiative reflection experiments."""
import re

from dante.models import InitiativeFeedback, InitiativeFeedbackCheck, InitiativeReflection


class InitiativeFeedbackEvaluator:
    """Check only program-verifiable structure; never score usefulness or progress."""

    VERSION = "deterministic-reflection-feedback-v2"
    ABSENCE_PATTERNS = {
        "results": (
            re.compile(r"\b(?:no|without|zero)\s+(?:prior|earlier|execution\s+)?(?:results?|outcomes?)\b", re.I),
            re.compile(r"\b(?:results?|outcomes?)\s+(?:are|were)\s+empty\b", re.I),
            re.compile(r"\bthere\s+(?:are|were)\s+no\s+(?:prior|earlier|execution\s+)?(?:results?|outcomes?)\b", re.I),
        ),
        "summaries": (
            re.compile(r"\b(?:no|without|zero)\s+(?:earlier\s+)?selected\s+summar(?:y|ies)\b", re.I),
            re.compile(r"\bselected\s+summar(?:y|ies)\s+(?:are|were)\s+empty\b", re.I),
            re.compile(r"\bno\s+earlier\s+initiative\s+decisions\b", re.I),
        ),
    }

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text.casefold()).strip()

    def evaluate(
        self,
        cycle_id: str,
        reflection: InitiativeReflection,
        *,
        available_evidence_ids: set[str],
        prior_results: int | None = None,
        prior_selected_summaries: int | None = None,
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
        supplied_text = " ".join(
            [reflection.response, *reflection.inferences, *reflection.unknowns]
        )
        claims_results = any(
            pattern.search(supplied_text)
            for pattern in self.ABSENCE_PATTERNS["results"]
        )
        claims_summaries = any(
            pattern.search(supplied_text)
            for pattern in self.ABSENCE_PATTERNS["summaries"]
        )
        if prior_results is None and prior_selected_summaries is None:
            absence_check = InitiativeFeedbackCheck(
                check_id="false_absence_claim",
                status="not_applicable",
                message="Supplied-history counts were not provided; absence claims were not evaluated.",
            )
        else:
            false_results = claims_results and (prior_results or 0) > 0
            false_summaries = claims_summaries and (prior_selected_summaries or 0) > 0
            if false_results or false_summaries:
                categories = []
                if false_results:
                    categories.append("results/outcomes")
                if false_summaries:
                    categories.append("selected summaries")
                absence_check = InitiativeFeedbackCheck(
                    check_id="false_absence_claim",
                    status="fail",
                    message=(
                        "Heuristic detected an absence claim about "
                        + " and ".join(categories)
                        + " even though supplied history was non-empty. "
                        "It may miss paraphrases or flag unusual wording."
                    ),
                )
            else:
                absence_check = InitiativeFeedbackCheck(
                    check_id="false_absence_claim",
                    status="pass",
                    message=(
                        "No false absence claim detected by the documented heuristic; "
                        "it may miss paraphrases or flag unusual wording."
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
        if absence_check.status == "fail":
            guidance.append("Supplied history is non-empty; do not claim it is empty.")
        guidance.append(
            "A proposed check is not an executed check; do not describe it as progress."
        )
        return InitiativeFeedback(
            cycle_id=cycle_id,
            checks=[citation_check, separation_check, execution_check, absence_check],
            guidance=guidance,
        )
