from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from agent.ranking_agent import RankingAgent


class RankingAgentTests(unittest.TestCase):
    def build_match(
        self,
        name: str = "Example Scholarship",
        compatibility_score: int = 80,
        eligibility_decision: str = "possible_match",
        risk_factors: list[str] | None = None,
        missing_requirements: list[str] | None = None,
        source_reliability_score: int = 5,
    ) -> dict:
        return {
            "scholarship_name": name,
            "source_url": f"https://example.edu/{name.lower().replace(' ', '-')}",
            "compatibility_score": compatibility_score,
            "eligibility_decision": eligibility_decision,
            "matched_factors": ["Field and country align."],
            "missing_requirements": missing_requirements or [],
            "risk_factors": risk_factors or [],
            "score_breakdown": {
                "nationality_score": 20,
                "academic_level_score": 20,
                "field_score": 20,
                "target_country_score": 15,
                "language_score": 15,
                "funding_score": 5,
                "source_reliability_score": source_reliability_score,
                "deadline_status_score": 5,
            },
            "recommendation_reason": "Profile is compatible with the opportunity.",
        }

    def test_strong_match_with_high_compatibility_becomes_high_priority(self) -> None:
        result = RankingAgent().rank_recommendations(
            [
                self.build_match(
                    compatibility_score=85,
                    eligibility_decision="strong_match",
                )
            ]
        )[0]

        self.assertEqual(result["priority_label"], "high_priority")
        self.assertGreaterEqual(result["final_score"], 80)

    def test_not_eligible_becomes_not_recommended(self) -> None:
        result = RankingAgent().rank_recommendations(
            [
                self.build_match(
                    compatibility_score=85,
                    eligibility_decision="not_eligible",
                    missing_requirements=["Application status is closed."],
                )
            ]
        )[0]

        self.assertEqual(result["priority_label"], "not_recommended")

    def test_weak_match_receives_penalty(self) -> None:
        possible = RankingAgent().rank_recommendations(
            [self.build_match(compatibility_score=70, eligibility_decision="possible_match")]
        )[0]
        weak = RankingAgent().rank_recommendations(
            [self.build_match(compatibility_score=70, eligibility_decision="weak_match")]
        )[0]

        self.assertLess(weak["final_score"], possible["final_score"])

    def test_insufficient_information_receives_moderate_penalty(self) -> None:
        possible = RankingAgent().rank_recommendations(
            [self.build_match(compatibility_score=70, eligibility_decision="possible_match")]
        )[0]
        unclear = RankingAgent().rank_recommendations(
            [
                self.build_match(
                    compatibility_score=70,
                    eligibility_decision="insufficient_information",
                )
            ]
        )[0]

        self.assertLess(unclear["final_score"], possible["final_score"])
        self.assertGreater(unclear["final_score"], 0)

    def test_risk_factors_reduce_final_score(self) -> None:
        clean = RankingAgent().rank_recommendations([self.build_match()])[0]
        risky = RankingAgent().rank_recommendations(
            [self.build_match(risk_factors=["Deadline is unknown and needs confirmation."])]
        )[0]

        self.assertLess(risky["final_score"], clean["final_score"])

    def test_missing_requirements_reduce_final_score(self) -> None:
        clean = RankingAgent().rank_recommendations([self.build_match()])[0]
        missing = RankingAgent().rank_recommendations(
            [self.build_match(missing_requirements=["Required language may be missing: German."])]
        )[0]

        self.assertLess(missing["final_score"], clean["final_score"])

    def test_final_score_remains_between_zero_and_hundred(self) -> None:
        result = RankingAgent().rank_recommendations(
            [
                self.build_match(
                    compatibility_score=500,
                    eligibility_decision="strong_match",
                )
            ]
        )[0]

        self.assertGreaterEqual(result["final_score"], 0)
        self.assertLessEqual(result["final_score"], 100)

    def test_ranked_results_are_sorted_from_highest_to_lowest(self) -> None:
        results = RankingAgent().rank_recommendations(
            [
                self.build_match("Low", compatibility_score=55),
                self.build_match("High", compatibility_score=90),
                self.build_match("Medium", compatibility_score=70),
            ]
        )

        scores = [result["final_score"] for result in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_rank_numbers_are_assigned_correctly(self) -> None:
        results = RankingAgent().rank_recommendations(
            [
                self.build_match("First", compatibility_score=90),
                self.build_match("Second", compatibility_score=80),
            ]
        )

        self.assertEqual([result["rank"] for result in results], [1, 2])

    def test_ranking_max_results_is_respected(self) -> None:
        fake_settings = SimpleNamespace(
            RANKING_MAX_RESULTS=2,
            RANKING_MIN_FINAL_SCORE=50,
        )
        matches = [
            self.build_match("One", compatibility_score=90),
            self.build_match("Two", compatibility_score=80),
            self.build_match("Three", compatibility_score=70),
        ]

        with patch("agent.ranking_agent.settings", fake_settings):
            results = RankingAgent().rank_recommendations(matches)

        self.assertEqual(len(results), 2)


if __name__ == "__main__":
    unittest.main()
