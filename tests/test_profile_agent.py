from __future__ import annotations

import unittest

from agent.profile_agent import ProfileAgent
from schemas.profile_schema import ProfileValidationError
from utils.normalizer import (
    normalize_language_entries,
    normalize_language_profiles,
    normalize_list,
)
from utils.profile_normalization import infer_profile_from_text


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
        self.assertEqual(normalized_profile["academic_level"], "master")
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

    def test_spanish_typo_profile_is_normalized(self) -> None:
        raw_profile = (
            "soy colmbiano estudio ing sistemas quiero beca de maestria "
            "en ia en almania hablo ingles b2"
        )

        normalized_profile = self.agent.prepare_profile(infer_profile_from_text(raw_profile))

        self.assertEqual(normalized_profile["nationality"], "Colombian")
        self.assertEqual(normalized_profile["country_of_origin"], "Colombia")
        self.assertEqual(normalized_profile["academic_level"], "master")
        self.assertEqual(normalized_profile["field_of_study"], "Computer Science")
        self.assertEqual(normalized_profile["specialization"], "Artificial Intelligence")
        self.assertIn("Germany", normalized_profile["target_countries"])
        self.assertIn(
            {"language": "English", "level": "B2", "display": "English B2"},
            normalized_profile["languages"],
        )
        self.assertIn(
            {"language": "Spanish", "level": "Native", "display": "Spanish Native"},
            normalized_profile["languages"],
        )
        self.assertEqual(normalized_profile["raw_profile_text"], raw_profile)
        self.assertTrue(normalized_profile["normalization_warnings"])

    def test_mixed_language_profile_is_normalized(self) -> None:
        raw_profile = (
            "I am from Ecuador, estudio software, quiero beca completa para "
            "master en AI en Canada, hablo español e ingles C1"
        )

        normalized_profile = self.agent.prepare_profile(infer_profile_from_text(raw_profile))

        self.assertEqual(normalized_profile["nationality"], "Ecuadorian")
        self.assertEqual(normalized_profile["country_of_origin"], "Ecuador")
        self.assertEqual(normalized_profile["academic_level"], "master")
        self.assertEqual(normalized_profile["specialization"], "Artificial Intelligence")
        self.assertIn("Canada", normalized_profile["target_countries"])
        self.assertEqual(normalized_profile["scholarship_type"], "Full funding")
        self.assertIn(
            {"language": "Spanish", "level": "Native", "display": "Spanish Native"},
            normalized_profile["languages"],
        )
        self.assertIn(
            {"language": "English", "level": "C1", "display": "English C1"},
            normalized_profile["languages"],
        )

    def test_ambiguous_profile_generates_warnings_without_crashing(self) -> None:
        raw_profile = "quiero una beca para estudiar afuera"

        normalized_profile = self.agent.prepare_profile(infer_profile_from_text(raw_profile))

        self.assertEqual(normalized_profile["academic_level"], "unspecified")
        self.assertEqual(normalized_profile["field_of_study"], "General studies")
        self.assertEqual(normalized_profile["target_countries"], ["Global"])
        self.assertTrue(normalized_profile["normalization_warnings"])
        self.assertTrue(
            any(
                "academic level" in warning.casefold()
                for warning in normalized_profile["normalization_warnings"]
            )
        )

    def test_valid_spanish_profile_passes_minimum_validation_and_builds_intent(self) -> None:
        raw_profile = (
            "Soy colombiano, hablo español nativo e inglés B2, busco beca completa "
            "para maestría en inteligencia artificial en Canadá."
        )

        normalized_profile = self.agent.prepare_profile(infer_profile_from_text(raw_profile))
        validation = self.agent.validate_minimum_required_input(normalized_profile)
        search_intent = self.agent.build_search_intent(normalized_profile)

        self.assertEqual(validation["status"], "ready")
        self.assertEqual(normalized_profile["country_of_origin"], "Colombia")
        self.assertEqual(search_intent["country_or_nationality"], "Colombia")
        self.assertIn(
            {"language": "Spanish", "level": "Native", "display": "Spanish Native"},
            search_intent["languages"],
        )
        self.assertIn(
            {"language": "English", "level": "B2", "display": "English B2"},
            search_intent["languages"],
        )
        self.assertEqual(search_intent["scholarship_type"], "Full funding")
        self.assertEqual(search_intent["academic_level"], "master")
        self.assertEqual(search_intent["field_of_study"], "Computer Science")
        self.assertEqual(search_intent["specialization"], "Artificial Intelligence")
        self.assertEqual(search_intent["target_countries"], ["Canada"])
        self.assertEqual(search_intent["search_specificity"], "specific")
        self.assertIn("search_signature", search_intent)

    def test_typo_heavy_profile_passes_minimum_validation(self) -> None:
        raw_profile = (
            "soy colmbiano hablo ingles b2 y español busco beca parcial "
            "para tecnologia"
        )

        normalized_profile = self.agent.prepare_profile(infer_profile_from_text(raw_profile))
        validation = self.agent.validate_minimum_required_input(normalized_profile)
        search_intent = self.agent.build_search_intent(normalized_profile)

        self.assertEqual(validation["status"], "ready")
        self.assertEqual(search_intent["country_or_nationality"], "Colombia")
        self.assertIn(
            {"language": "English", "level": "B2", "display": "English B2"},
            search_intent["languages"],
        )
        self.assertIn(
            {"language": "Spanish", "level": "Native", "display": "Spanish Native"},
            search_intent["languages"],
        )
        self.assertEqual(search_intent["scholarship_type"], "Partial funding")
        self.assertEqual(search_intent["field_of_study"], "Technology")

    def test_missing_scholarship_type_fails_minimum_validation(self) -> None:
        raw_profile = (
            "Soy ecuatoriano, hablo español e inglés, quiero estudiar computer science."
        )

        normalized_profile = self.agent.prepare_profile(infer_profile_from_text(raw_profile))
        validation = self.agent.validate_minimum_required_input(normalized_profile)

        self.assertEqual(validation["status"], "needs_more_information")
        self.assertIn("scholarship_type", validation["missing_required_fields"])

    def test_ecuadorian_written_profile_with_combined_funding_passes(self) -> None:
        raw_profile = (
            "I am Ecuadorian and I am studying Information Technology. I speak "
            "Spanish as my native language and English at a B1 level. I am "
            "interested in Cybersecurity, Cloud Computing, Programming, and "
            "Software Development. I am looking for partial or full scholarships "
            "for undergraduate studies, preferably in Spain, Canada, Chile, or "
            "the United States. My budget is limited, and I can contribute up to "
            "5,000 USD per year. I prefer hybrid or on-campus programs."
        )

        normalized_profile = self.agent.prepare_profile(infer_profile_from_text(raw_profile))
        validation = self.agent.validate_minimum_required_input(normalized_profile)
        search_intent = self.agent.build_search_intent(normalized_profile)

        self.assertEqual(validation["status"], "ready")
        self.assertEqual(search_intent["country_or_nationality"], "Ecuador")
        self.assertEqual(search_intent["scholarship_type"], "Full or partial funding")
        self.assertEqual(search_intent["academic_level"], "undergraduate")
        self.assertEqual(search_intent["field_of_study"], "Information Technology")
        self.assertEqual(
            set(search_intent["target_countries"]),
            {"Spain", "Canada", "Chile", "United States"},
        )
        self.assertEqual(search_intent["budget"]["max_personal_contribution"], 5000)
        self.assertIn(search_intent["modality"], {"Hybrid", "On-campus"})
        self.assertIn(
            {"language": "Spanish", "level": "Native", "display": "Spanish Native"},
            search_intent["languages"],
        )
        self.assertIn(
            {"language": "English", "level": "B1", "display": "English B1"},
            search_intent["languages"],
        )

    def test_short_ecuadorian_profile_with_partial_or_full_passes(self) -> None:
        raw_profile = (
            "I am Ecuadorian and I speak Spanish and English B1. I am looking "
            "for partial or full scholarships for undergraduate studies in "
            "Information Technology."
        )

        normalized_profile = self.agent.prepare_profile(infer_profile_from_text(raw_profile))
        validation = self.agent.validate_minimum_required_input(normalized_profile)
        search_intent = self.agent.build_search_intent(normalized_profile)

        self.assertEqual(validation["status"], "ready")
        self.assertEqual(search_intent["scholarship_type"], "Full or partial funding")
        self.assertEqual(search_intent["academic_level"], "undergraduate")
        self.assertEqual(search_intent["field_of_study"], "Information Technology")

    def test_full_or_partial_scholarships_are_detected(self) -> None:
        raw_profile = (
            "I am Ecuadorian and I speak Spanish and English B1. I am looking "
            "for full or partial scholarships for undergraduate studies in "
            "Information Technology."
        )

        normalized_profile = self.agent.prepare_profile(infer_profile_from_text(raw_profile))
        validation = self.agent.validate_minimum_required_input(normalized_profile)

        self.assertEqual(validation["status"], "ready")
        self.assertEqual(
            normalized_profile["scholarship_type"],
            "Full or partial funding",
        )

    def test_spanish_combined_scholarship_type_is_detected(self) -> None:
        raw_profile = (
            "Soy ecuatoriano, hablo espaÃ±ol e inglÃ©s B1. Busco becas completas "
            "o parciales para pregrado en tecnologÃ­a de la informaciÃ³n."
        )

        normalized_profile = self.agent.prepare_profile(infer_profile_from_text(raw_profile))
        validation = self.agent.validate_minimum_required_input(normalized_profile)
        search_intent = self.agent.build_search_intent(normalized_profile)

        self.assertEqual(validation["status"], "ready")
        self.assertEqual(search_intent["scholarship_type"], "Full or partial funding")
        self.assertEqual(search_intent["field_of_study"], "Information Technology")

    def test_typo_spanish_combined_scholarship_type_passes(self) -> None:
        raw_profile = (
            "soy ecuatoriano hablo espanol e ingles b1 busco becas parciales "
            "o completas para pregrado en tecnologia"
        )

        normalized_profile = self.agent.prepare_profile(infer_profile_from_text(raw_profile))
        validation = self.agent.validate_minimum_required_input(normalized_profile)
        search_intent = self.agent.build_search_intent(normalized_profile)

        self.assertEqual(validation["status"], "ready")
        self.assertEqual(search_intent["scholarship_type"], "Full or partial funding")
        self.assertEqual(search_intent["field_of_study"], "Technology")

    def test_ecuadorian_profile_without_scholarship_type_still_fails(self) -> None:
        raw_profile = "Soy ecuatoriano, hablo espaÃ±ol e inglÃ©s B1 y estudio tecnologÃ­a."

        normalized_profile = self.agent.prepare_profile(infer_profile_from_text(raw_profile))
        validation = self.agent.validate_minimum_required_input(normalized_profile)

        self.assertEqual(validation["status"], "needs_more_information")
        self.assertIn("scholarship_type", validation["missing_required_fields"])

    def test_no_modality_is_omitted_from_search_intent_and_signature(self) -> None:
        raw_profile = (
            "Soy colombiano, hablo español e inglés B2, busco beca completa "
            "para maestría en inteligencia artificial."
        )

        normalized_profile = self.agent.prepare_profile(infer_profile_from_text(raw_profile))
        search_intent = self.agent.build_search_intent(normalized_profile)

        self.assertNotIn("modality", search_intent)
        self.assertNotIn("modality", search_intent["search_signature"]["payload"])

    def test_demo_defaults_are_not_injected_into_search_intent(self) -> None:
        raw_profile = (
            "Soy peruano, hablo inglés B2 y español, busco beca parcial "
            "para tecnología."
        )

        normalized_profile = self.agent.prepare_profile(infer_profile_from_text(raw_profile))
        validation = self.agent.validate_minimum_required_input(normalized_profile)
        search_intent = self.agent.build_search_intent(normalized_profile)

        self.assertEqual(validation["status"], "ready")
        self.assertNotIn("target_countries", search_intent)
        self.assertNotIn("Canada", search_intent.get("target_countries", []))
        self.assertNotIn("Germany", search_intent.get("target_countries", []))
        self.assertNotIn("Netherlands", search_intent.get("target_countries", []))


if __name__ == "__main__":
    unittest.main()
