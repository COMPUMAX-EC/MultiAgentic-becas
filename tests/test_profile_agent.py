from __future__ import annotations

import unittest

from agent.profile_agent import ProfileAgent
from schemas.profile_schema import ProfileValidationError
from utils.normalizer import (
    normalize_language_entries,
    normalize_language_profiles,
    normalize_list,
)


class ProfileAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = ProfileAgent()
        self.valid_profile = {
            "nationality": "  colombian ",
            "country_of_residence": "colombia",
            "languages": [" spanish ", "English", "english"],
            "academic_level": "masters",
            "field_of_study": " computer science ",
            "interests": [" AI ", "Data Science", "data science"],
            "target_countries": [" canada ", "Germany"],
            "scholarship_type": " full funding ",
            "budget": {"currency": " usd ", "max_personal_contribution": 5000},
            "preferred_modality": " online ",
        }

    def test_prepare_profile_normalizes_valid_profile(self) -> None:
        normalized_profile = self.agent.prepare_profile(self.valid_profile)

        self.assertEqual(normalized_profile["nationality"], "Colombian")
        self.assertEqual(normalized_profile["country_of_residence"], "Colombia")
        self.assertEqual(
            normalized_profile["languages"],
            [
                {"language": "Spanish", "level": None, "display": "Spanish"},
                {"language": "English", "level": None, "display": "English"},
            ],
        )
        self.assertEqual(normalized_profile["academic_level"], "Master")
        self.assertEqual(normalized_profile["interests"], ["AI", "Data Science"])
        self.assertEqual(normalized_profile["target_countries"], ["Canada", "Germany"])
        self.assertEqual(normalized_profile["budget"]["currency"], "usd")

    def test_prepare_profile_raises_for_missing_required_field(self) -> None:
        invalid_profile = dict(self.valid_profile)
        invalid_profile.pop("languages")

        with self.assertRaises(ProfileValidationError):
            self.agent.prepare_profile(invalid_profile)

    def test_normalize_language_entries(self) -> None:
        self.assertEqual(
            normalize_language_entries([" english ", "SPANISH", "english"]),
            ["English", "Spanish"],
        )

    def test_prepare_profile_accepts_structured_languages(self) -> None:
        structured_profile = dict(self.valid_profile)
        structured_profile["languages"] = [
            {"language": "Spanish", "level": "Native"},
            {"language": "English", "level": "b2"},
        ]

        normalized_profile = self.agent.prepare_profile(structured_profile)

        self.assertEqual(
            normalized_profile["languages"],
            [
                {"language": "Spanish", "level": "Native", "display": "Spanish Native"},
                {"language": "English", "level": "B2", "display": "English B2"},
            ],
        )

    def test_empty_languages_list_fails(self) -> None:
        invalid_profile = dict(self.valid_profile)
        invalid_profile["languages"] = []

        with self.assertRaises(ProfileValidationError):
            self.agent.prepare_profile(invalid_profile)

    def test_language_object_without_language_fails(self) -> None:
        invalid_profile = dict(self.valid_profile)
        invalid_profile["languages"] = [{"level": "B2"}]

        with self.assertRaises(ProfileValidationError):
            self.agent.prepare_profile(invalid_profile)

    def test_language_levels_are_preserved(self) -> None:
        self.assertEqual(
            normalize_language_profiles(
                [
                    {"language": "Spanish", "level": "Native"},
                    "english b2",
                ]
            ),
            [
                {"language": "Spanish", "level": "Native", "display": "Spanish Native"},
                {"language": "English", "level": "B2", "display": "English B2"},
            ],
        )

    def test_normalize_list(self) -> None:
        self.assertEqual(
            normalize_list([" AI ", "", "Data Science", "data science", None]),
            ["AI", "Data Science"],
        )


if __name__ == "__main__":
    unittest.main()
