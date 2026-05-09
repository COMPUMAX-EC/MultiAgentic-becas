from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory

from agent.ranking_agent import RankingAgent
from database.repository import list_ranking_records


class RankingAgentTests(unittest.TestCase):
    def build_match(
        self,
        name: str = "Example Scholarship",
        compatibility_score: int = 80,
        eligibility_decision: str = "likely_match",
        risk_factors: list[str] | None = None,
        missing_requirements: list[str] | None = None,
        source_reliability_score: int = 5,
        source_type: str = "university",
    ) -> dict:
        return {
            "scholarship_name": name,
            "source_url": f"https://example.edu/{name.lower().replace(' ', '-')}",
            "display_link": f"https://example.edu/{name.lower().replace(' ', '-')}",
            "source_type": source_type,
            "source_validation_status": "accepted_with_warning"
            if source_type.startswith("verified_")
            else "accepted",
            "compatibility_score": compatibility_score,
            "compatibility_points": 8,
            "max_possible_points": 10,
            "matched_profile_fields": ["field_of_study: Computer Science compatible"],
            "missing_profile_fields": missing_requirements or [],
            "source_trust_score": 70 if source_type.startswith("verified_") else 100,
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
                    eligibility_decision="confirmed_match",
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

    def test_rejected_becomes_rejected_priority(self) -> None:
        result = RankingAgent().rank_recommendations(
            [
                self.build_match(
                    compatibility_score=85,
                    eligibility_decision="rejected",
                    missing_requirements=["No useful traceable link is available."],
                )
            ]
        )[0]

        self.assertEqual(result["priority_label"], "rejected")

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

    def test_ranking_does_not_cap_ranked_results(self) -> None:
        matches = [
            self.build_match("One", compatibility_score=90),
            self.build_match("Two", compatibility_score=80),
            self.build_match("Three", compatibility_score=70),
        ]

        results = RankingAgent().rank_recommendations(matches)

        self.assertEqual(len(results), 3)

    def test_incomplete_compatible_scholarship_can_remain_possible(self) -> None:
        result = RankingAgent().rank_recommendations(
            [
                self.build_match(
                    compatibility_score=58,
                    eligibility_decision="possible_match",
                    risk_factors=[
                        "Deadline is unknown and needs confirmation.",
                        "Language requirements are not clearly specified.",
                    ],
                    missing_requirements=[],
                )
            ]
        )[0]

        self.assertIn(result["priority_label"], {"medium_priority", "possible_match", "low_priority"})
        self.assertNotEqual(result["priority_label"], "not_recommended")

    def test_unknown_deadline_is_small_penalty_only(self) -> None:
        result = RankingAgent().rank_recommendations(
            [
                self.build_match(
                    compatibility_score=70,
                    eligibility_decision="likely_match",
                    risk_factors=["Deadline is unknown and needs confirmation."],
                )
            ]
        )[0]

        self.assertGreaterEqual(result["final_score"], 60)
        self.assertNotEqual(result["priority_label"], "not_recommended")

    def test_missing_nationality_is_not_hard_rejected(self) -> None:
        result = RankingAgent().rank_recommendations(
            [
                self.build_match(
                    compatibility_score=68,
                    eligibility_decision="likely_match",
                    risk_factors=["Eligible nationalities are not clearly specified."],
                )
            ]
        )[0]

        self.assertIn(result["priority_label"], {"high_priority", "medium_priority", "possible_match"})

    def test_explicit_nationality_mismatch_is_not_recommended(self) -> None:
        result = RankingAgent().rank_recommendations(
            [
                self.build_match(
                    compatibility_score=50,
                    eligibility_decision="mismatch",
                    missing_requirements=["Nationality list does not include Colombian applicants."],
                )
            ]
        )[0]

        self.assertEqual(result["priority_label"], "not_recommended")

    def test_verified_informational_source_good_match_is_not_rejected(self) -> None:
        result = RankingAgent().rank_recommendations(
            [
                self.build_match(
                    compatibility_score=66,
                    eligibility_decision="likely_match",
                    source_reliability_score=4,
                    source_type="verified_news",
                )
            ]
        )[0]

        self.assertIn(result["priority_label"], {"medium_priority", "possible_match"})

    def test_no_useful_link_is_excluded_by_ranking_validation(self) -> None:
        match = self.build_match(compatibility_score=80, eligibility_decision="likely_match")
        match["source_url"] = ""
        match["display_link"] = ""

        agent = RankingAgent()
        results = agent.rank_recommendations([match])

        self.assertEqual(results, [])
        self.assertEqual(agent.ranking_errors, [])

    def test_modality_conflict_lowers_priority_without_rejection(self) -> None:
        result = RankingAgent().rank_recommendations(
            [
                self.build_match(
                    compatibility_score=72,
                    eligibility_decision="likely_match",
                    risk_factors=["Scholarship modality conflicts with the user's stated preference."],
                )
            ]
        )[0]

        self.assertNotEqual(result["priority_label"], "rejected")
        self.assertGreaterEqual(result["final_score"], 45)

    def test_ranking_fields_are_preserved(self) -> None:
        result = RankingAgent().rank_recommendations([self.build_match()])[0]

        self.assertEqual(result["compatibility_points"], 8)
        self.assertEqual(result["max_possible_points"], 10)
        self.assertEqual(result["source_trust_score"], 100)
        self.assertEqual(
            result["matched_profile_fields"],
            ["field_of_study: Computer Science compatible"],
        )

    def test_ranking_records_are_persisted_by_profile_signature(self) -> None:
        with TemporaryDirectory() as temp_dir:
            db_path = f"{temp_dir}/ranking.sqlite3"
            match = self.build_match("Stored", compatibility_score=88)
            match["profile_signature"] = "profile-123"

            RankingAgent(db_path=db_path).rank_recommendations([match])
            records = list_ranking_records("profile-123", db_path=db_path)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["scholarship_name"], "Stored")
        self.assertEqual(records[0]["compatibility_points"], 8)


if __name__ == "__main__":
    unittest.main()
