from __future__ import annotations

from config.settings import settings
from schemas.ranking_schema import RankingValidationError, build_ranking_result
from utils.url_utils import first_useful_url


DECISION_ADJUSTMENTS = {
    "confirmed_match": 8,
    "likely_match": 4,
    "possible_match": 0,
    "insufficient_information": -3,
    "mismatch": -25,
    "rejected": -100,
    # Backward-compatible labels from the earlier matcher.
    "strong_match": 10,
    "weak_match": -5,
    "not_eligible": -35,
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
        for scored_result in limited_results:
            if not self._has_useful_link(scored_result):
                continue
            ranking_result = build_ranking_result(
                rank=len(ranked_results) + 1,
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
            ranking_result.update(
                {
                    "display_link": scored_result.get("display_link"),
                    "official_link": scored_result.get("official_link"),
                    "application_url": scored_result.get("application_url"),
                    "pdf_url": scored_result.get("pdf_url"),
                    "original_url": scored_result.get("original_url"),
                    "query_used": scored_result.get("query_used"),
                    "source_type": scored_result.get("source_type"),
                }
            )
            ranked_results.append(ranking_result)

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

        if not self._has_useful_link(matching_result):
            final_score = 0
            eligibility_decision = "rejected"
            ranking_reasons.append("No useful traceable link is available.")

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

        link_adjustment = self._link_adjustment(matching_result)
        final_score += link_adjustment
        if link_adjustment:
            ranking_reasons.append("A useful display link improves traceability.")

        risk_penalty = self._risk_penalty(risk_factors)
        if risk_penalty:
            final_score -= risk_penalty
            ranking_reasons.append(
                f"Risk factors reduce the score by {risk_penalty} points."
            )

        missing_penalty = self._missing_penalty(missing_requirements)
        if missing_penalty:
            final_score -= missing_penalty
            ranking_reasons.append(
                f"Missing requirements reduce the score by {missing_penalty} points."
            )

        if self._has_expired_or_closed_signal(matching_result):
            final_score -= 40
            ranking_reasons.append(
                "Expired or closed application signals strongly reduce recommendation value."
            )

        if eligibility_decision in {"mismatch", "not_eligible"}:
            final_score = min(final_score, 29)
        if eligibility_decision == "weak_match":
            final_score = min(final_score, 44)
        if eligibility_decision == "possible_match":
            final_score = min(final_score, 59)
        if eligibility_decision == "insufficient_information":
            final_score = min(final_score, 44)
        if eligibility_decision == "rejected":
            final_score = 0

        final_score = self._clamp_score(final_score)
        priority_label = self._priority_label(final_score, eligibility_decision)

        return {
            "scholarship_name": matching_result.get("scholarship_name"),
            "source_url": matching_result.get("source_url"),
            "display_link": matching_result.get("display_link"),
            "official_link": matching_result.get("official_link"),
            "application_url": matching_result.get("application_url"),
            "pdf_url": matching_result.get("pdf_url"),
            "original_url": matching_result.get("original_url"),
            "query_used": matching_result.get("query_used"),
            "source_type": matching_result.get("source_type"),
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
            return 5
        if source_score >= 4:
            return 4
        if source_score >= 3:
            return 2
        return 0

    def _priority_label(self, final_score: int, eligibility_decision: str) -> str:
        if eligibility_decision == "rejected":
            return "rejected"
        if eligibility_decision in {"mismatch", "not_eligible"} or final_score < 30:
            return "not_recommended"
        if eligibility_decision == "insufficient_information" and final_score < 45:
            return "insufficient_information"
        if final_score >= 80:
            return "high_priority"
        if final_score >= 60:
            return "medium_priority"
        if final_score >= 45:
            return "possible_match"
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
        if priority_label == "possible_match":
            return reason or "Traceable option with partial compatibility and details to confirm."
        if priority_label == "low_priority":
            if risk_factors:
                return f"Lower priority because {risk_factors[0].rstrip('.').lower()}."
            return reason or "Potential option, but the fit is limited."
        if priority_label == "rejected":
            if risk_factors:
                return f"Rejected because {risk_factors[0].rstrip('.').lower()}."
            return "Rejected because a hard validation or eligibility blocker was found."
        if missing_requirements:
            return f"Not recommended because {missing_requirements[0].rstrip('.').lower()}."
        if risk_factors:
            return f"Not recommended because {risk_factors[0].rstrip('.').lower()}."
        return f"Not recommended with final score {final_score}."

    def _risk_penalty(self, risk_factors: list[str]) -> int:
        penalty = 0
        for risk in risk_factors:
            risk_key = risk.casefold()
            if "deadline is unknown" in risk_key or "could not be verified" in risk_key:
                penalty += 1
            elif "not clearly specified" in risk_key or "needs confirmation" in risk_key:
                penalty += 1
            elif "conflicts" in risk_key or "incompatible" in risk_key:
                penalty += 4
            else:
                penalty += 2
        return min(8, penalty)

    def _missing_penalty(self, missing_requirements: list[str]) -> int:
        penalty = 0
        for requirement in missing_requirements:
            requirement_key = requirement.casefold()
            if "deadline" in requirement_key or "language" in requirement_key:
                penalty += 1
            elif "nationality" in requirement_key or "academic level" in requirement_key:
                penalty += 4
            elif "field" in requirement_key:
                penalty += 3
            else:
                penalty += 1
        return min(10, penalty)

    def _link_adjustment(self, matching_result: dict) -> int:
        if first_useful_url(matching_result.get("official_link")):
            return 4
        if first_useful_url(matching_result.get("application_url")):
            return 3
        if first_useful_url(
            matching_result.get("display_link"), matching_result.get("source_url")
        ):
            return 2
        if first_useful_url(matching_result.get("pdf_url")):
            return 1
        return 0

    def _has_useful_link(self, matching_result: dict) -> bool:
        return bool(
            first_useful_url(
                matching_result.get("display_link"),
                matching_result.get("official_link"),
                matching_result.get("application_url"),
                matching_result.get("source_url"),
                matching_result.get("pdf_url"),
            )
        )

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
            "possible_match": 2,
            "low_priority": 3,
            "insufficient_information": 4,
            "not_recommended": 5,
            "rejected": 5,
        }.get(priority_label, 5)

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
