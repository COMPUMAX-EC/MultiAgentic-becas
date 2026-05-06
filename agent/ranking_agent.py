from __future__ import annotations

from config.settings import settings
from schemas.ranking_schema import RankingValidationError, build_ranking_result


DECISION_ADJUSTMENTS = {
    "strong_match": 10,
    "possible_match": 0,
    "weak_match": -15,
    "not_eligible": -50,
    "insufficient_information": -20,
}

EXPIRED_OR_CLOSED_TERMS = (
    "expired",
    "closed",
    "deadline passed",
    "deadline appears to have passed",
    "applications are marked as closed",
    "application status is closed",
)


class RankingAgent:
    def __init__(self) -> None:
        self.ranking_errors: list[dict] = []

    def rank_recommendations(self, matching_results: list[dict]) -> list[dict]:
        self.ranking_errors = []
        scored_results: list[dict] = []

        for matching_result in matching_results:
            try:
                scored_results.append(self._score_matching_result(matching_result))
            except (
                RankingValidationError,
                AttributeError,
                TypeError,
                ValueError,
            ) as exc:
                self.ranking_errors.append(
                    {
                        "scholarship_name": matching_result.get("scholarship_name"),
                        "source_url": matching_result.get("source_url"),
                        "error": str(exc),
                    }
                )

        scored_results.sort(
            key=lambda result: (
                result["final_score"],
                result["compatibility_score"],
                -self._priority_sort_value(result["priority_label"]),
            ),
            reverse=True,
        )

        limited_results = scored_results[: settings.RANKING_MAX_RESULTS]
        ranked_results: list[dict] = []
        for index, scored_result in enumerate(limited_results, start=1):
            ranked_results.append(
                build_ranking_result(
                    rank=index,
                    scholarship_name=scored_result["scholarship_name"],
                    source_url=scored_result["source_url"],
                    final_score=scored_result["final_score"],
                    compatibility_score=scored_result["compatibility_score"],
                    eligibility_decision=scored_result["eligibility_decision"],
                    priority_label=scored_result["priority_label"],
                    ranking_reasons=scored_result["ranking_reasons"],
                    risk_factors=scored_result["risk_factors"],
                    missing_requirements=scored_result["missing_requirements"],
                    recommendation_summary=scored_result["recommendation_summary"],
                    score_breakdown=scored_result["score_breakdown"],
                )
            )

        return ranked_results

    def _score_matching_result(self, matching_result: dict) -> dict:
        compatibility_score = self._clamp_score(
            matching_result.get("compatibility_score")
        )
        eligibility_decision = str(
            matching_result.get("eligibility_decision") or "insufficient_information"
        )
        risk_factors = self._clean_list(matching_result.get("risk_factors"))
        missing_requirements = self._clean_list(
            matching_result.get("missing_requirements")
        )
        score_breakdown = matching_result.get("score_breakdown") or {}
        if not isinstance(score_breakdown, dict):
            score_breakdown = {}

        final_score = compatibility_score
        ranking_reasons: list[str] = [
            f"Base compatibility score is {compatibility_score}."
        ]

        decision_adjustment = DECISION_ADJUSTMENTS.get(eligibility_decision, -20)
        final_score += decision_adjustment
        ranking_reasons.append(
            self._describe_decision_adjustment(
                eligibility_decision, decision_adjustment
            )
        )

        source_adjustment = self._source_reliability_adjustment(score_breakdown)
        final_score += source_adjustment
        if source_adjustment > 0:
            ranking_reasons.append("Source reliability improves ranking confidence.")

        risk_penalty = min(15, len(risk_factors) * 3)
        if risk_penalty:
            final_score -= risk_penalty
            ranking_reasons.append(
                f"Risk factors reduce the score by {risk_penalty} points."
            )

        missing_penalty = min(20, len(missing_requirements) * 5)
        if missing_penalty:
            final_score -= missing_penalty
            ranking_reasons.append(
                f"Missing requirements reduce the score by {missing_penalty} points."
            )

        if self._has_expired_or_closed_signal(matching_result):
            final_score -= 30
            ranking_reasons.append(
                "Expired or closed application signals strongly reduce recommendation value."
            )

        if eligibility_decision == "not_eligible":
            final_score = min(final_score, settings.RANKING_MIN_FINAL_SCORE - 1)

        final_score = self._clamp_score(final_score)
        priority_label = self._priority_label(final_score, eligibility_decision)

        return {
            "scholarship_name": matching_result.get("scholarship_name"),
            "source_url": matching_result.get("source_url"),
            "final_score": final_score,
            "compatibility_score": compatibility_score,
            "eligibility_decision": eligibility_decision,
            "priority_label": priority_label,
            "ranking_reasons": ranking_reasons,
            "risk_factors": risk_factors,
            "missing_requirements": missing_requirements,
            "recommendation_summary": self._recommendation_summary(
                priority_label,
                final_score,
                matching_result.get("recommendation_reason"),
                risk_factors,
                missing_requirements,
            ),
            "score_breakdown": score_breakdown,
        }

    def _describe_decision_adjustment(
        self, eligibility_decision: str, adjustment: int
    ) -> str:
        if adjustment > 0:
            return f"{eligibility_decision} increases the score by {adjustment} points."
        if adjustment < 0:
            return f"{eligibility_decision} reduces the score by {abs(adjustment)} points."
        return f"{eligibility_decision} keeps the compatibility score unchanged."

    def _source_reliability_adjustment(self, score_breakdown: dict) -> int:
        source_score = self._clamp_score(
            score_breakdown.get("source_reliability_score", 0)
        )
        if source_score >= 5:
            return 3
        if source_score >= 4:
            return 2
        if source_score >= 3:
            return 1
        return 0

    def _priority_label(self, final_score: int, eligibility_decision: str) -> str:
        if eligibility_decision == "not_eligible" or final_score < 50:
            return "not_recommended"
        if final_score >= 80:
            return "high_priority"
        if final_score >= 65:
            return "medium_priority"
        return "low_priority"

    def _recommendation_summary(
        self,
        priority_label: str,
        final_score: int,
        recommendation_reason: object,
        risk_factors: list[str],
        missing_requirements: list[str],
    ) -> str:
        reason = str(recommendation_reason or "").strip()
        if priority_label == "high_priority":
            return reason or "Strong recommendation based on high compatibility and low risk."
        if priority_label == "medium_priority":
            return reason or "Good candidate with a few details to confirm."
        if priority_label == "low_priority":
            if risk_factors:
                return f"Lower priority because {risk_factors[0].rstrip('.').lower()}."
            return reason or "Potential option, but the fit is limited."
        if missing_requirements:
            return f"Not recommended because {missing_requirements[0].rstrip('.').lower()}."
        if risk_factors:
            return f"Not recommended because {risk_factors[0].rstrip('.').lower()}."
        return f"Not recommended with final score {final_score}."

    def _has_expired_or_closed_signal(self, matching_result: dict) -> bool:
        text_parts = [
            matching_result.get("eligibility_decision"),
            matching_result.get("recommendation_reason"),
            " ".join(self._clean_list(matching_result.get("risk_factors"))),
            " ".join(self._clean_list(matching_result.get("missing_requirements"))),
        ]
        text = " ".join(str(part or "") for part in text_parts).casefold()
        return any(term in text for term in EXPIRED_OR_CLOSED_TERMS)

    def _priority_sort_value(self, priority_label: str) -> int:
        return {
            "high_priority": 0,
            "medium_priority": 1,
            "low_priority": 2,
            "not_recommended": 3,
        }.get(priority_label, 4)

    def _clean_list(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _clamp_score(self, value: object) -> int:
        try:
            score = int(value)
        except (TypeError, ValueError):
            score = 0
        return max(0, min(100, score))
