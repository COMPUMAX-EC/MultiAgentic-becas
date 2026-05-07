from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.query_agent import QueryAgent, QueryGenerationError
from schemas.search_schema import validate_generated_queries


class QueryAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.normalized_profile = {
            "nationality": "Colombian",
            "country_of_residence": "Colombia",
            "languages": ["Spanish", "English"],
            "academic_level": "Bachelor",
            "field_of_study": "Computer Science",
            "interests": ["Artificial Intelligence", "Data Science"],
            "target_countries": ["Canada", "Germany"],
            "scholarship_type": "Partial funding",
            "budget": {"currency": "usd", "max_personal_contribution": 8000},
            "preferred_modality": "On-campus",
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
