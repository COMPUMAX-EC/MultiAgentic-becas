from __future__ import annotations

import json
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from agent.query_agent import QueryAgent, QueryGenerationError
from llm.provider import LLMProviderError
from schemas.search_schema import validate_generated_queries


class QueryAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.normalized_profile = {
            "nationality": "Colombian",
            "country_of_origin": "Colombia",
            "country_of_residence": "Colombia",
            "languages": ["Spanish", "English"],
            "academic_level": "master",
            "field_of_study": "Computer Science",
            "specialization": "Artificial Intelligence",
            "interests": ["Artificial Intelligence", "Data Science"],
            "target_countries": ["Canada", "Germany"],
            "scholarship_type": "Full funding",
            "budget": {"currency": "usd", "max_personal_contribution": 8000},
            "preferred_modality": "Any",
        }
        self.specific_search_intent_profile = {
            "search_intent": {
                "country_or_nationality": "Colombia",
                "languages": [
                    {"language": "Spanish", "level": "Native", "display": "Spanish Native"},
                    {"language": "English", "level": "B2", "display": "English B2"},
                ],
                "scholarship_type": "Full funding",
                "academic_level": "master",
                "field_of_study": "Computer Science",
                "specialization": "Artificial Intelligence",
                "target_countries": ["Canada"],
                "search_specificity": "specific",
            }
        }

    def test_build_prompt_uses_normalized_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prompt_path = Path(temp_dir) / "prompt.txt"
            prompt_path.write_text("Generate queries.", encoding="utf-8")

            prompt = QueryAgent(prompt_template_path=prompt_path).build_prompt(
                self.normalized_profile
            )

        self.assertIn("Generate queries.", prompt)
        self.assertIn('"nationality": "Colombian"', prompt)
        self.assertIn('"target_countries"', prompt)

    @patch("agent.query_agent.generate_text")
    def test_generate_queries_parses_valid_json(self, mock_generate_text) -> None:
        mock_generate_text.return_value = json.dumps(
            {
                "queries": [
                    {
                        "query": "official Canada AI bachelor scholarships Colombian students",
                        "target_country": "Canada",
                        "reason": "Targets official Canadian scholarship pages.",
                        "priority": "1",
                    }
                ]
            }
        )

        queries = QueryAgent().generate_queries(self.normalized_profile)

        self.assertGreaterEqual(len(queries), 1)
        self.assertEqual(queries[0]["priority"], 1)
        self.assertTrue(
            any("site:.edu" in query["query"] for query in queries),
            "Deterministic official-source query families should be appended.",
        )

    def test_deterministic_queries_cover_global_source_families(self) -> None:
        queries = QueryAgent().build_deterministic_query_families(
            self.normalized_profile
        )
        query_text = "\n".join(query["query"].casefold() for query in queries)

        self.assertGreater(len(queries), 5)
        self.assertIn("university scholarships", query_text)
        self.assertIn("government scholarships", query_text)
        self.assertIn("foundation scholarships", query_text)
        self.assertIn("organization scholarships", query_text)
        self.assertIn("research institute scholarships", query_text)
        self.assertIn("company scholarships", query_text)
        self.assertIn("international organization scholarships", query_text)
        self.assertIn("verified scholarship news", query_text)
        self.assertTrue(any(query["target_country"] == "Canada" for query in queries))
        self.assertTrue(any(query["target_country"] == "Germany" for query in queries))

    def test_query_family_coverage_from_specific_search_intent(self) -> None:
        queries = QueryAgent().build_deterministic_query_families(
            self.specific_search_intent_profile
        )
        query_families = {query["query_family"] for query in queries}
        source_families = {query["source_family"] for query in queries}
        query_text = "\n".join(query["query"] for query in queries)

        self.assertTrue(
            {
                "destination",
                "nationality",
                "field",
                "academic_level",
                "scholarship_type",
                "university",
                "government",
                "embassy",
                "international_organization",
                "foundation",
                "company",
                "professional_association",
                "verified_secondary_source",
            }.issubset(query_families)
        )
        self.assertTrue(
            {
                "university",
                "government",
                "embassy",
                "international_organization",
                "foundation",
                "company",
                "professional_association",
            }.issubset(source_families)
        )
        self.assertTrue(any(query["target_country"] == "Canada" for query in queries))
        self.assertIn("Canada", query_text)
        self.assertNotIn("Germany", query_text)
        self.assertNotIn("Netherlands", query_text)
        self.assertNotIn("Spain", query_text)
        self.assertNotIn("United States", query_text)

    def test_general_valid_search_intent_does_not_invent_optional_fields(self) -> None:
        profile = {
            "search_intent": {
                "country_or_nationality": "Ecuadorian",
                "languages": [{"language": "Spanish", "level": None, "display": "Spanish"}],
                "scholarship_type": "Partial funding",
                "search_specificity": "general",
            }
        }

        queries = QueryAgent().build_deterministic_query_families(profile)
        query_text = "\n".join(query["query"] for query in queries)

        self.assertTrue(queries)
        self.assertIn("Ecuadorian", query_text)
        self.assertIn("Partial funding", query_text)
        self.assertNotIn("Canada", query_text)
        self.assertNotIn("Germany", query_text)
        self.assertNotIn("Artificial Intelligence", query_text)
        self.assertTrue(all(query["target_country"] == "global" for query in queries))

    def test_modality_is_omitted_when_any_or_missing(self) -> None:
        profile_without_modality = dict(self.normalized_profile)
        profile_without_modality["preferred_modality"] = "Any"

        queries = QueryAgent().build_deterministic_query_families(
            profile_without_modality
        )

        self.assertFalse(
            any("online scholarships" in query["query"].casefold() for query in queries)
        )

    def test_explicit_online_modality_adds_some_online_queries(self) -> None:
        online_profile = dict(self.normalized_profile)
        online_profile["preferred_modality"] = "online"

        queries = QueryAgent().build_deterministic_query_families(online_profile)

        self.assertTrue(
            any("online scholarships" in query["query"].casefold() for query in queries)
        )

    def test_query_metadata_survives_validation(self) -> None:
        queries = validate_generated_queries(
            [
                {
                    "query": "Canada university scholarships",
                    "target_country": "Canada",
                    "reason": "Metadata test.",
                    "priority": 1,
                    "query_family": "university",
                    "source_family": "university",
                    "expansion_round": 1,
                }
            ]
        )

        self.assertEqual(queries[0]["query_family"], "university")
        self.assertEqual(queries[0]["source_family"], "university")
        self.assertEqual(queries[0]["expansion_round"], 1)


    def test_validate_generated_queries_deduplicates_repeated_queries(self) -> None:
        queries = validate_generated_queries(
            [
                {
                    "query": "Canada AI scholarships",
                    "target_country": "Canada",
                    "reason": "First.",
                    "priority": 1,
                },
                {
                    "query": " canada ai scholarships ",
                    "target_country": "Canada",
                    "reason": "Duplicate.",
                    "priority": 2,
                },
            ]
        )

        self.assertEqual(len(queries), 1)

    @patch("agent.query_agent.generate_text")
    def test_search_query_limit_comes_from_settings(self, mock_generate_text) -> None:
        mock_generate_text.side_effect = LLMProviderError("offline")

        with patch(
            "agent.query_agent.settings",
            SimpleNamespace(SEARCH_MAX_QUERIES=7),
        ):
            queries = QueryAgent().generate_queries(self.normalized_profile)

        self.assertEqual(len(queries), 7)

    @patch("agent.query_agent.generate_text")
    def test_generate_queries_rejects_empty_query_values(self, mock_generate_text) -> None:
        mock_generate_text.return_value = json.dumps(
            {
                "queries": [
                    {
                        "query": "",
                        "target_country": "Canada",
                        "reason": "Empty query should be rejected.",
                        "priority": 1,
                    }
                ]
            }
        )

        with self.assertRaises(QueryGenerationError):
            QueryAgent().generate_queries(self.normalized_profile)


if __name__ == "__main__":
    unittest.main()
