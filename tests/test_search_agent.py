from __future__ import annotations

import unittest
from types import SimpleNamespace
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

        with patch(
            "agent.search_agent.settings",
            SimpleNamespace(
                SEARCH_MAX_QUERIES=10,
                SEARCH_MAX_RESULTS_PER_QUERY=3,
                SEARCH_MAX_GLOBAL_CANDIDATES=150,
                MIN_RECOMMENDED_RESULTS_BEFORE_EXPANSION=5,
                MAX_EXPANSION_ROUNDS=2,
            ),
        ):
            results = SearchAgent().search([self.generated_queries[0]])

        self.assertEqual(len(results), 3)

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
        self.assertEqual(results[0]["query_used"], self.generated_queries[0]["query"])
        self.assertEqual(results[0]["target_country"], "Canada")
        self.assertEqual(results[0]["priority"], 1)
        self.assertEqual(results[0]["source_domain"], "example.org")
        self.assertIn("source_type", results[0])

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

    @patch("agent.search_agent.search_web")
    def test_search_executes_configured_query_limit(self, mock_search_web) -> None:
        mock_search_web.return_value = [
            {
                "title": "Result",
                "url": "https://example.org/result",
                "snippet": "Snippet",
                "source": "duckduckgo",
                "query": "ignored",
            }
        ]
        generated_queries = [
            {
                "query": f"query {index}",
                "target_country": "global",
                "reason": "limit test",
                "priority": index,
            }
            for index in range(1, 4)
        ]

        with patch(
            "agent.search_agent.settings",
            SimpleNamespace(
                SEARCH_MAX_QUERIES=1,
                SEARCH_MAX_RESULTS_PER_QUERY=20,
                SEARCH_MAX_GLOBAL_CANDIDATES=150,
                MIN_RECOMMENDED_RESULTS_BEFORE_EXPANSION=5,
                MAX_EXPANSION_ROUNDS=2,
            ),
        ):
            SearchAgent().search(generated_queries)

        self.assertEqual(mock_search_web.call_count, 1)

    @patch("agent.search_agent.search_web")
    def test_search_caps_global_candidates_from_settings(self, mock_search_web) -> None:
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

        with patch(
            "agent.search_agent.settings",
            SimpleNamespace(
                SEARCH_MAX_QUERIES=10,
                SEARCH_MAX_RESULTS_PER_QUERY=20,
                SEARCH_MAX_GLOBAL_CANDIDATES=4,
                MIN_RECOMMENDED_RESULTS_BEFORE_EXPANSION=5,
                MAX_EXPANSION_ROUNDS=2,
            ),
        ):
            results = SearchAgent().search([self.generated_queries[0]])

        self.assertEqual(len(results), 4)

    @patch("agent.search_agent.search_web")
    def test_search_deduplicates_repeated_candidate_urls(self, mock_search_web) -> None:
        mock_search_web.return_value = [
            {
                "title": "Scholarship One",
                "url": "https://example.org/scholarship/",
                "snippet": "Snippet",
                "source": "duckduckgo",
                "query": "ignored",
            },
            {
                "title": "Scholarship One duplicate",
                "url": "https://example.org/scholarship",
                "snippet": "Snippet",
                "source": "duckduckgo",
                "query": "ignored",
            },
        ]

        results = SearchAgent().search([self.generated_queries[0]])

        self.assertEqual(len(results), 1)

    @patch("agent.search_agent.search_web")
    def test_search_infers_preliminary_source_family(self, mock_search_web) -> None:
        mock_search_web.return_value = [
            {
                "title": "Government scholarship",
                "url": "https://education.gov.example/scholarship",
                "snippet": "Government program for international students.",
                "source": "duckduckgo",
                "query": "ignored",
            }
        ]

        results = SearchAgent().search([self.generated_queries[0]])

        self.assertEqual(results[0]["source_type"], "government")

    @patch("agent.search_agent.search_web")
    def test_search_preserves_query_family_and_source_family(self, mock_search_web) -> None:
        mock_search_web.return_value = [
            {
                "title": "University Scholarship",
                "url": "https://example.edu/scholarship",
                "snippet": "Scholarship for international students.",
                "source": "duckduckgo",
                "query": "ignored",
            }
        ]
        query = dict(self.generated_queries[0])
        query["query_family"] = "university"
        query["source_family"] = "university"
        query["expansion_round"] = 1

        results = SearchAgent().search([query])

        self.assertEqual(results[0]["query_family"], "university")
        self.assertEqual(results[0]["source_family"], "university")
        self.assertEqual(results[0]["expansion_round"], 1)

    @patch("agent.search_agent.search_web")
    def test_search_deduplicates_tracking_parameter_urls_and_keeps_metadata(
        self,
        mock_search_web,
    ) -> None:
        mock_search_web.return_value = [
            {
                "title": "Scholarship One",
                "url": "https://example.org/scholarship?utm_source=newsletter",
                "snippet": "Short.",
                "source": "duckduckgo",
                "query": "ignored",
            },
            {
                "title": "Scholarship One",
                "url": "https://example.org/scholarship",
                "snippet": "Longer scholarship snippet with useful metadata.",
                "source": "duckduckgo",
                "query": "ignored",
            },
        ]
        query = dict(self.generated_queries[0])
        query["query_family"] = "destination"
        query["source_family"] = "foundation"

        results = SearchAgent().search([query])

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["url"], "https://example.org/scholarship")
        self.assertEqual(results[0]["source_family"], "foundation")
        self.assertIn("Longer scholarship snippet", results[0]["snippet"])

    @patch("agent.search_agent.search_web")
    def test_expansion_round_runs_when_initial_candidate_count_is_weak(
        self,
        mock_search_web,
    ) -> None:
        mock_search_web.side_effect = [
            [
                {
                    "title": "Initial Result",
                    "url": "https://example.org/initial",
                    "snippet": "Scholarship.",
                    "source": "duckduckgo",
                    "query": "ignored",
                }
            ],
            [
                {
                    "title": "Expansion Result",
                    "url": "https://example.edu/expansion",
                    "snippet": "Expanded scholarship.",
                    "source": "duckduckgo",
                    "query": "ignored",
                }
            ],
        ]
        queries = [
            {
                "query": "initial scholarship query",
                "target_country": "global",
                "reason": "Initial.",
                "priority": 1,
                "query_family": "nationality",
                "source_family": "unknown",
                "expansion_round": 0,
            },
            {
                "query": "expanded university scholarship query",
                "target_country": "global",
                "reason": "Expansion.",
                "priority": 2,
                "query_family": "university",
                "source_family": "university",
                "expansion_round": 1,
            },
        ]

        with patch(
            "agent.search_agent.settings",
            SimpleNamespace(
                SEARCH_MAX_QUERIES=10,
                SEARCH_MAX_RESULTS_PER_QUERY=20,
                SEARCH_MAX_GLOBAL_CANDIDATES=300,
                MIN_RECOMMENDED_RESULTS_BEFORE_EXPANSION=5,
                MAX_EXPANSION_ROUNDS=2,
            ),
        ):
            agent = SearchAgent()
            results = agent.search(queries)

        self.assertEqual(mock_search_web.call_count, 2)
        self.assertEqual(agent.last_expansion_rounds_used, 1)
        self.assertEqual(len(results), 2)

    @patch("agent.search_agent.search_web")
    def test_expansion_round_is_skipped_when_initial_candidates_are_enough(
        self,
        mock_search_web,
    ) -> None:
        mock_search_web.return_value = [
            {
                "title": f"Initial Result {index}",
                "url": f"https://example.org/initial-{index}",
                "snippet": "Scholarship.",
                "source": "duckduckgo",
                "query": "ignored",
            }
            for index in range(5)
        ]
        queries = [
            {
                "query": "initial scholarship query",
                "target_country": "global",
                "reason": "Initial.",
                "priority": 1,
                "query_family": "nationality",
                "source_family": "unknown",
                "expansion_round": 0,
            },
            {
                "query": "expanded university scholarship query",
                "target_country": "global",
                "reason": "Expansion.",
                "priority": 2,
                "query_family": "university",
                "source_family": "university",
                "expansion_round": 1,
            },
        ]

        with patch(
            "agent.search_agent.settings",
            SimpleNamespace(
                SEARCH_MAX_QUERIES=10,
                SEARCH_MAX_RESULTS_PER_QUERY=20,
                SEARCH_MAX_GLOBAL_CANDIDATES=300,
                MIN_RECOMMENDED_RESULTS_BEFORE_EXPANSION=5,
                MAX_EXPANSION_ROUNDS=2,
            ),
        ):
            agent = SearchAgent()
            results = agent.search(queries)

        self.assertEqual(mock_search_web.call_count, 1)
        self.assertEqual(agent.last_expansion_rounds_used, 0)
        self.assertEqual(len(results), 5)

    def test_default_search_limits_are_centralized_in_settings(self) -> None:
        from config.settings import settings

        self.assertGreaterEqual(settings.SEARCH_MAX_QUERIES, 30)
        self.assertGreaterEqual(settings.SEARCH_MAX_RESULTS_PER_QUERY, 20)
        self.assertGreaterEqual(settings.SEARCH_MAX_GLOBAL_CANDIDATES, 300)
        self.assertGreaterEqual(settings.MIN_RECOMMENDED_RESULTS_BEFORE_EXPANSION, 5)
        self.assertGreaterEqual(settings.MAX_EXPANSION_ROUNDS, 2)


if __name__ == "__main__":
    unittest.main()
