import unittest
from unittest.mock import patch

from api.server import normalize_frontend_response, run_live_search_pipeline


class FakeQueryAgent:
    def generate_queries(self, normalized_profile: dict) -> list[dict]:
        return [
            {"query": "ai scholarship", "target_country": "Germany", "priority": 1},
            {"query": "data scholarship", "target_country": "Canada", "priority": 2},
        ]


class FakeSearchAgent:
    last_raw_results_count = 4
    last_deduplicated_count = 3

    def search(self, queries: list[dict]) -> list[dict]:
        return [
            {"title": "Official", "url": "https://example.edu/official"},
            {"title": "News", "url": "https://news.example.com/call"},
            {"title": "Blog", "url": "https://blog.example.com/post"},
        ]


class FakeSourceValidatorAgent:
    def validate_sources(self, candidate_results: list[dict]) -> list[dict]:
        return [
            {
                "title": "Official",
                "url": "https://example.edu/official",
                "source_url": "https://example.edu/official",
                "decision": "accept",
                "validation_status": "accepted",
                "acceptance_status": "accepted",
                "source_type": "university",
            },
            {
                "title": "News",
                "url": "https://news.example.com/call",
                "source_url": "https://news.example.com/call",
                "decision": "review",
                "validation_status": "accepted_with_warning",
                "acceptance_status": "accepted_with_warning",
                "source_type": "verified_news",
            },
            {
                "title": "Blog",
                "url": "https://blog.example.com/post",
                "decision": "reject",
                "validation_status": "rejected",
                "acceptance_status": "rejected",
                "source_type": "irrelevant",
                "risk_flags": ["low_relevance"],
            },
        ]


class FakePageReaderAgent:
    def read_pages(self, accepted_sources: list[dict]) -> list[dict]:
        return [
            {
                "url": "https://example.edu/official",
                "source_url": "https://example.edu/official",
                "title": "Official",
                "status": "read_success",
                "cleaned_text": "Scholarship content",
            },
            {
                "url": "https://news.example.com/call",
                "source_url": "https://news.example.com/call",
                "title": "News",
                "status": "read_failed",
                "cleaned_text": "",
            },
        ]


class FakeExtractionAgent:
    extraction_errors = [{"url": "https://news.example.com/call", "error": "Read failed"}]

    def extract_scholarships(self, page_results: list[dict]) -> list[dict]:
        return [
            {
                "scholarship_name": "Good Scholarship",
                "source_url": "https://example.edu/official",
                "display_link": "https://example.edu/official",
                "application_status": "open",
            },
            {
                "scholarship_name": "No Link Scholarship",
                "application_status": "open",
            },
            {
                "scholarship_name": "Expired Scholarship",
                "source_url": "https://example.edu/expired",
                "display_link": "https://example.edu/expired",
                "application_status": "closed",
            },
        ]


def fake_run_matching(normalized_profile: dict, scholarships: list[dict]) -> dict:
    return {
        "summary": {"errors": []},
        "matching_results": [
            {
                "scholarship_name": "Good Scholarship",
                "source_url": "https://example.edu/official",
                "display_link": "https://example.edu/official",
                "compatibility_score": 80,
                "eligibility_decision": "likely_match",
                "risk_factors": [],
                "missing_requirements": [],
                "score_breakdown": {"source_reliability_score": 5},
                "recommendation_reason": "Good fit.",
            }
        ],
    }


def fake_run_ranking(matching_results: list[dict]) -> dict:
    return {
        "summary": {"errors": []},
        "ranked_results": [
            {
                "rank": 1,
                "scholarship_name": "Good Scholarship",
                "source_url": "https://example.edu/official",
                "display_link": "https://example.edu/official",
                "final_score": 82,
                "compatibility_score": 80,
                "eligibility_decision": "likely_match",
                "priority_label": "high_priority",
                "ranking_reasons": ["Good fit."],
                "risk_factors": [],
                "missing_requirements": [],
                "recommendation_summary": "Good fit.",
                "score_breakdown": {"source_reliability_score": 5},
            }
        ],
    }


class PipelineMetricsTests(unittest.TestCase):
    def test_live_pipeline_returns_real_metrics_and_rejection_summary(self) -> None:
        payload = self._run_fake_pipeline()

        metrics = payload["metrics"]
        self.assertEqual(metrics["generated_queries_count"], 2)
        self.assertEqual(metrics["sources_found_count"], 4)
        self.assertEqual(metrics["sources_deduplicated_count"], 3)
        self.assertEqual(metrics["expansion_rounds_used"], 0)
        self.assertEqual(metrics["untrusted_sources_skipped_count"], 0)
        self.assertEqual(metrics["secondary_guidance_sources_count"], 1)
        self.assertEqual(metrics["sources_accepted_count"], 1)
        self.assertEqual(metrics["sources_accepted_with_warning_count"], 1)
        self.assertEqual(metrics["sources_rejected_count"], 1)
        self.assertEqual(metrics["pages_read_count"], 1)
        self.assertEqual(metrics["pages_failed_count"], 1)
        self.assertEqual(metrics["scholarships_extracted_count"], 3)
        self.assertEqual(metrics["scholarships_with_useful_link_count"], 1)
        self.assertEqual(metrics["expired_rejected_count"], 1)
        self.assertEqual(metrics["matched_count"], 1)
        self.assertEqual(metrics["ranked_count"], 1)
        self.assertEqual(metrics["recommended_count"], 1)
        self.assertEqual(metrics["less_recommended_count"], 0)

        rejection_summary = payload["rejection_summary"]
        self.assertEqual(rejection_summary["duplicate"], 1)
        self.assertEqual(rejection_summary["known_untrusted_source"], 0)
        self.assertEqual(rejection_summary["non_scholarship_page"], 1)
        self.assertEqual(rejection_summary["validation_failed"], 0)
        self.assertEqual(rejection_summary["read_failed"], 1)
        self.assertEqual(rejection_summary["extraction_failed"], 1)
        self.assertEqual(rejection_summary["expired_or_closed"], 1)
        self.assertEqual(rejection_summary["no_useful_link"], 1)
        self.assertEqual(rejection_summary["profile_missing_required_fields"], 0)
        self.assertEqual(rejection_summary["other"], 0)

    def test_metrics_are_internally_consistent(self) -> None:
        metrics = self._run_fake_pipeline()["metrics"]

        self.assertGreaterEqual(
            metrics["sources_found_count"], metrics["sources_deduplicated_count"]
        )
        self.assertGreaterEqual(
            metrics["sources_deduplicated_count"],
            metrics["sources_accepted_count"]
            + metrics["sources_accepted_with_warning_count"],
        )
        self.assertGreaterEqual(metrics["ranked_count"], metrics["recommended_count"])
        self.assertGreaterEqual(metrics["ranked_count"], metrics["less_recommended_count"])
        self.assertGreaterEqual(
            metrics["scholarships_extracted_count"],
            metrics["scholarships_with_useful_link_count"],
        )

    def test_workflow_counts_reflect_metrics(self) -> None:
        payload = self._run_fake_pipeline()
        metrics = payload["metrics"]
        steps = {step["step_name"]: step for step in payload["workflow_steps"]}

        self.assertEqual(
            steps["Generating global scholarship queries"]["count"],
            metrics["generated_queries_count"],
        )
        self.assertEqual(
            steps["Searching global sources"]["count"],
            metrics["sources_found_count"],
        )
        self.assertEqual(
            steps["Deduplicating candidates"]["count"],
            metrics["sources_deduplicated_count"],
        )
        self.assertEqual(
            steps["Validating trusted sources"]["count"],
            metrics["sources_accepted_count"]
            + metrics["sources_accepted_with_warning_count"],
        )
        self.assertEqual(
            steps["Extracting scholarship data"]["count"],
            metrics["scholarships_extracted_count"],
        )
        self.assertEqual(
            steps["Resolving useful links"]["count"],
            metrics["scholarships_with_useful_link_count"],
        )
        self.assertEqual(
            steps["Scoring compatibility"]["count"],
            metrics["matched_count"],
        )
        self.assertEqual(
            steps["Ranking recommendations"]["count"],
            metrics["ranked_count"],
        )

    def test_required_workflow_steps_are_present(self) -> None:
        payload = self._run_fake_pipeline()
        step_names = [step["step_name"] for step in payload["workflow_steps"]]
        allowed_statuses = {"pending", "running", "completed", "skipped", "failed"}

        for expected_step in (
            "Reading profile input",
            "Normalizing profile",
            "Building search intent",
            "Generating global scholarship queries",
            "Searching global sources",
            "Deduplicating candidates",
            "Validating trusted sources",
            "Reading scholarship pages",
            "Extracting scholarship data",
            "Resolving useful links",
            "Scoring compatibility",
            "Ranking recommendations",
            "Preparing final results",
        ):
            self.assertIn(expected_step, step_names)
        for step in payload["workflow_steps"]:
            self.assertIn(step["status"], allowed_statuses)

    def test_frontend_response_preserves_metrics_object(self) -> None:
        payload = self._run_fake_pipeline()
        response = normalize_frontend_response(
            payload,
            status_override=payload["status"],
            message=payload["message"],
            extra_workflow_steps=payload["workflow_steps"],
        )

        self.assertIn("metrics", response)
        self.assertIn("rejection_summary", response)
        self.assertIn("workflow_steps", response)
        self.assertEqual(
            response["metrics"]["ranked_count"],
            len(response["ranked_results"]),
        )
        self.assertEqual(
            response["metrics"]["recommended_count"],
            len(response["recommended"]),
        )
        self.assertLessEqual(len(response["less_recommended"]), 10)
        for result in [*response["recommended"], *response["less_recommended"]]:
            self.assertTrue(result["display_link"])

    def _run_fake_pipeline(self) -> dict:
        with patch("api.server.QUERY_AGENT", FakeQueryAgent()), patch(
            "api.server.SEARCH_AGENT", FakeSearchAgent()
        ), patch("api.server.SOURCE_VALIDATOR_AGENT", FakeSourceValidatorAgent()), patch(
            "api.server.PAGE_READER_AGENT", FakePageReaderAgent()
        ), patch("api.server.EXTRACTION_AGENT", FakeExtractionAgent()), patch(
            "api.server.run_matching", fake_run_matching
        ), patch(
            "api.server.run_ranking", fake_run_ranking
        ):
            workflow_steps = [
                {
                    "step_name": "Reading profile input",
                    "status": "completed",
                    "count": 1,
                    "message": "Profile input received.",
                },
                {
                    "step_name": "Normalizing profile",
                    "status": "completed",
                    "count": 1,
                    "message": "Profile input received and normalized.",
                },
            ]
            return run_live_search_pipeline({"academic_level": "master"}, workflow_steps)


if __name__ == "__main__":
    unittest.main()
