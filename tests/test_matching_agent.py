from __future__ import annotations

import unittest
from unittest.mock import patch

from agent.matching_agent import MatchingAgent


class MatchingAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = {
            "nationality": "Colombian",
            "country_of_residence": "Colombia",
            "languages": ["Spanish", "English"],
            "academic_level": "Bachelor",
            "field_of_study": "Computer Science",
            "interests": ["Artificial Intelligence", "Data Science"],
            "target_countries": ["Canada", "Germany"],
            "scholarship_type": "Partial funding",
            "budget": {
                "currency": "usd",
                "max_personal_contribution": 8000,
            },
            "preferred_modality": "On-campus",
        }
        self.base_scholarship = {
            "scholarship_name": "AI Excellence Scholarship",
            "institution": "Example University",
            "country": "Canada",
            "academic_level": "Undergraduate",
            "eligible_nationalities": ["Colombian"],
            "required_languages": ["English"],
            "fields": ["Computer Science"],
            "benefits": ["Full tuition and living allowance"],
            "deadline": "2026-12-31",
            "requirements": ["Academic merit"],
            "application_status": "open",
            "source_url": "https://example.edu/scholarships/ai-excellence",
            "source_type": "official_university",
            "source_reliability_score": 90,
            "extraction_confidence": 85,
            "evidence_snippets": ["Computer Science scholarship for international students."],
        }

    def test_strong_match_when_core_factors_align(self) -> None:
        result = MatchingAgent().match_scholarship(self.profile, self.base_scholarship)

        self.assertIn(result["eligibility_decision"], {"confirmed_match", "likely_match"})
        self.assertGreaterEqual(result["compatibility_score"], 80)

    def test_possible_match_when_nationality_is_unknown(self) -> None:
        scholarship = dict(self.base_scholarship)
        scholarship["eligible_nationalities"] = []

        result = MatchingAgent().match_scholarship(self.profile, scholarship)

        self.assertIn(result["eligibility_decision"], {"likely_match", "possible_match"})
        self.assertIn(
            "Eligible nationalities are not clearly specified.",
            result["risk_factors"],
        )

    def test_not_eligible_when_application_status_is_closed(self) -> None:
        scholarship = dict(self.base_scholarship)
        scholarship["application_status"] = "closed"

        result = MatchingAgent().match_scholarship(self.profile, scholarship)

        self.assertEqual(result["eligibility_decision"], "rejected")

    def test_expired_deadline_produces_not_eligible(self) -> None:
        scholarship = dict(self.base_scholarship)
        scholarship["deadline"] = "2024-01-15"

        result = MatchingAgent().match_scholarship(self.profile, scholarship)

        self.assertEqual(result["eligibility_decision"], "rejected")

    def test_missing_language_requirement_creates_risk_factor(self) -> None:
        scholarship = dict(self.base_scholarship)
        scholarship["required_languages"] = ["German"]

        result = MatchingAgent().match_scholarship(self.profile, scholarship)

        self.assertTrue(
            any("Language requirement" in risk for risk in result["risk_factors"])
        )

    def test_unknown_deadline_creates_risk_factor(self) -> None:
        scholarship = dict(self.base_scholarship)
        scholarship["deadline"] = None

        result = MatchingAgent().match_scholarship(self.profile, scholarship)

        self.assertTrue(any("Deadline is unknown" in risk for risk in result["risk_factors"]))

    def test_compatibility_score_remains_between_zero_and_hundred(self) -> None:
        scholarship = dict(self.base_scholarship)
        scholarship["eligible_nationalities"] = ["Argentinian"]
        scholarship["required_languages"] = ["German"]
        scholarship["country"] = "Japan"
        scholarship["fields"] = ["History"]
        scholarship["source_reliability_score"] = 10

        result = MatchingAgent().match_scholarship(self.profile, scholarship)

        self.assertGreaterEqual(result["compatibility_score"], 0)
        self.assertLessEqual(result["compatibility_score"], 100)

    @patch("agent.matching_agent.generate_text")
    def test_matching_does_not_require_ollama_when_llm_is_disabled(
        self, mock_generate_text
    ) -> None:
        scholarship = dict(self.base_scholarship)
        scholarship["eligible_nationalities"] = []
        scholarship["fields"] = []
        scholarship["deadline"] = None

        result = MatchingAgent().match_scholarship(self.profile, scholarship)

        self.assertIn(
            result["eligibility_decision"],
            {"likely_match", "possible_match", "insufficient_information"},
        )
        mock_generate_text.assert_not_called()

    def test_incomplete_but_compatible_scholarship_is_not_rejected(self) -> None:
        scholarship = dict(self.base_scholarship)
        scholarship["eligible_nationalities"] = []
        scholarship["required_languages"] = []
        scholarship["benefits"] = []
        scholarship["deadline"] = None

        result = MatchingAgent().match_scholarship(self.profile, scholarship)

        self.assertNotIn(result["eligibility_decision"], {"rejected", "mismatch", "not_eligible"})
        self.assertGreaterEqual(result["compatibility_score"], 45)

    def test_missing_nationality_is_risk_only(self) -> None:
        scholarship = dict(self.base_scholarship)
        scholarship["eligible_nationalities"] = []

        result = MatchingAgent().match_scholarship(self.profile, scholarship)

        self.assertNotEqual(result["eligibility_decision"], "rejected")
        self.assertTrue(any("nationalities" in risk.lower() for risk in result["risk_factors"]))

    def test_explicit_nationality_mismatch_is_major_penalty(self) -> None:
        scholarship = dict(self.base_scholarship)
        scholarship["eligible_nationalities"] = ["Argentinian", "Brazilian"]

        result = MatchingAgent().match_scholarship(self.profile, scholarship)

        self.assertEqual(result["eligibility_decision"], "mismatch")
        self.assertTrue(any("nationality" in item.lower() for item in result["missing_requirements"]))

    def test_verified_informational_source_good_match_is_kept(self) -> None:
        scholarship = dict(self.base_scholarship)
        scholarship["source_type"] = "verified_news"
        scholarship["source_reliability_score"] = None

        result = MatchingAgent().match_scholarship(self.profile, scholarship)

        self.assertIn(result["eligibility_decision"], {"confirmed_match", "likely_match", "possible_match"})
        self.assertNotEqual(result["eligibility_decision"], "rejected")

    def test_no_modality_preference_does_not_penalize_different_modality(self) -> None:
        profile = dict(self.profile)
        profile["preferred_modality"] = "Any"
        scholarship = dict(self.base_scholarship)
        scholarship["modality"] = "online"

        result = MatchingAgent().match_scholarship(profile, scholarship)

        self.assertNotIn(
            "Scholarship modality conflicts with the user's stated preference.",
            result["risk_factors"],
        )

    def test_selected_modality_conflict_adds_risk_without_hard_rejection(self) -> None:
        scholarship = dict(self.base_scholarship)
        scholarship["modality"] = "online"

        result = MatchingAgent().match_scholarship(self.profile, scholarship)

        self.assertIn(
            "Scholarship modality conflicts with the user's stated preference.",
            result["risk_factors"],
        )
        self.assertNotEqual(result["eligibility_decision"], "rejected")


if __name__ == "__main__":
    unittest.main()
