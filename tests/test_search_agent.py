from __future__ import annotations

import unittest
from unittest.mock import patch

from agent.search_agent import SearchAgent
from tools.web_search import WebSearchError
from utils.deduplicator import deduplicate_by_url, normalize_url


class SearchAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.generated_queries = [
            {
                "query": "official Canada scholarships computer science",
                "target_country": "Canada",
                "reason": "Canada target",
                "priority": 1,
            },
            {
                "query": "official Germany scholarships computer science",
                "target_country": "Germany",
                "reason": "Germany target",
                "priority": 2,
            },
        ]

    def test_deduplicate_by_url_removes_trailing_slash_duplicates(self) -> None:
        deduplicated_results = deduplicate_by_url(
            [
                {"url": "https://example.org/scholarship/"},
                {"url": "https://example.org/scholarship"},
            ]
        )

        self.assertEqual(len(deduplicated_results), 1)
        self.assertEqual(
            normalize_url("https://example.org/scholarship/"),
            "https://example.org/scholarship",
        )

    @patch("agent.search_agent.search_web")
    def test_search_limits_results_per_query(self, mock_search_web) -> None:
        mock_search_web.return_value = [
            {
                "title": f"Result {index}",
                "url": f"https://example.org/{index}",
                "snippet": "Snippet",
                "source": "duckduckgo",
                "query": "ignored",
            }
            for index in range(10)
        ]

        results = SearchAgent().search([self.generated_queries[0]])

        self.assertEqual(len(results), 5)

    @patch("agent.search_agent.search_web")
    def test_search_preserves_query_metadata(self, mock_search_web) -> None:
        mock_search_web.return_value = [
            {
                "title": "Scholarship Result",
                "url": "https://example.org/result",
                "snippet": "Snippet",
                "source": "duckduckgo",
                "query": "ignored",
            }
        ]

        results = SearchAgent().search([self.generated_queries[0]])

        self.assertEqual(results[0]["query"], self.generated_queries[0]["query"])
        self.assertEqual(results[0]["target_country"], "Canada")
        self.assertEqual(results[0]["priority"], 1)

    @patch("agent.search_agent.search_web")
    def test_search_handles_provider_failure_without_crashing(self, mock_search_web) -> None:
        mock_search_web.side_effect = [
            WebSearchError("provider failed"),
            [
                {
                    "title": "German Result",
                    "url": "https://example.org/germany",
                    "snippet": "Snippet",
                    "source": "duckduckgo",
                    "query": "ignored",
                }
            ],
        ]

        results = SearchAgent().search(self.generated_queries)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["target_country"], "Germany")


if __name__ == "__main__":
    unittest.main()
