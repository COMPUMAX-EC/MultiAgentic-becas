from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from services.demo_service import DemoService


class StubProfileAgent:
    def prepare_profile(self, raw_profile_data: dict) -> dict:
        return raw_profile_data


class StubQueryAgent:
    def generate_queries(self, normalized_profile: dict) -> list[dict]:
        return [{"query": "test scholarship", "target_country": "Canada", "reason": "fit", "priority": 1}]


class StubSearchAgent:
    def search(self, queries: list[dict]) -> list[dict]:
        return [{"title": "Scholarship source", "url": "https://example.edu/scholarship", "snippet": "Funding", "query": queries[0]["query"], "target_country": "Canada"}]


class StubSourceValidatorAgent:
    def validate_sources(self, candidate_results: list[dict]) -> list[dict]:
        return [{"title": "Scholarship source", "url": "https://example.edu/scholarship", "snippet": "Funding", "query": "test scholarship", "target_country": "Canada", "decision": "accept"}]


class StubPageReaderAgent:
    def read_pages(self, validated_sources: list[dict]) -> list[dict]:
        return [{"url": validated_sources[0]["url"], "title": validated_sources[0]["title"], "status": "read_success", "cleaned_text": "Scholarship for Computer Science students", "source_type": "official_university", "source_decision": "accept"}]


class StubExtractionAgent:
    extraction_errors: list[dict] = []

    def extract_scholarships(self, page_results: list[dict]) -> list[dict]:
        return [{"scholarship_name": "Demo Scholarship", "source_url": page_results[0]["url"], "source_type": "official_university", "source_reliability_score": 90}]


class DemoServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name) / "demo"
        self.saved_json_payload = None

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_demo_service_builds_valid_workflow_result_with_mocked_agents(self) -> None:
        service = self._build_service()

        result = service.run()

        self.assertIn("demo_status", result)
        self.assertEqual(result["generated_queries_count"], 1)

    def test_demo_output_includes_workflow_steps(self) -> None:
        service = self._build_service()

        result = service.run()

        self.assertTrue(result["workflow_steps"])
        self.assertEqual(result["workflow_steps"][0]["step_name"], "profile_normalization")

    def test_demo_output_includes_top_recommendations(self) -> None:
        service = self._build_service()

        result = service.run()

        self.assertTrue(result["top_recommendations"])
        self.assertEqual(result["top_recommendations"][0]["scholarship_name"], "Demo Scholarship")

    def test_errors_are_collected_safely(self) -> None:
        class FailingQueryAgent(StubQueryAgent):
            def generate_queries(self, normalized_profile: dict) -> list[dict]:
                raise RuntimeError("query failed")

        service = self._build_service(query_agent=FailingQueryAgent())

        result = service.run()

        self.assertTrue(result["errors"])
        self.assertEqual(result["demo_status"], "failed")

    def test_output_paths_are_generated_under_demo_results_directory(self) -> None:
        service = self._build_service()

        result = service.run()

        self.assertIn(str(self.output_dir), result["output_files"]["json"])
        self.assertIn(str(self.output_dir), result["output_files"]["markdown"])

    def _build_service(self, query_agent=None) -> DemoService:
        def fake_load_json(profile_path: str | Path) -> dict:
            return {
                "nationality": "Colombian",
                "country_of_residence": "Colombia",
                "languages": ["Spanish", "English"],
                "academic_level": "Bachelor",
                "field_of_study": "Computer Science",
                "interests": ["Artificial Intelligence"],
                "target_countries": ["Canada"],
                "scholarship_type": "Partial funding",
                "budget": {"currency": "USD", "max_personal_contribution": 8000},
                "preferred_modality": "On-campus",
            }

        def fake_save_json(file_path: str | Path, payload: dict) -> None:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")
            self.saved_json_payload = payload

        def fake_matching_runner(normalized_profile: dict, scholarships: list[dict]) -> dict:
            return {
                "summary": {"errors": []},
                "matching_results": [
                    {
                        "scholarship_name": "Demo Scholarship",
                        "source_url": "https://example.edu/scholarship",
                        "compatibility_score": 82,
                        "eligibility_decision": "possible_match",
                        "matched_factors": ["Country fit"],
                        "missing_requirements": [],
                        "risk_factors": [],
                        "score_breakdown": {},
                        "recommendation_reason": "Looks promising.",
                    }
                ],
            }

        def fake_ranking_runner(matching_results: list[dict]) -> dict:
            return {
                "summary": {"errors": []},
                "ranked_results": [
                    {
                        "rank": 1,
                        "scholarship_name": "Demo Scholarship",
                        "final_score": 84,
                        "priority_label": "high_priority",
                        "recommendation_summary": "Strong fit.",
                        "source_url": "https://example.edu/scholarship",
                    }
                ],
            }

        service = DemoService(
            profile_agent=StubProfileAgent(),
            query_agent=query_agent or StubQueryAgent(),
            search_agent=StubSearchAgent(),
            source_validator_agent=StubSourceValidatorAgent(),
            page_reader_agent=StubPageReaderAgent(),
            extraction_agent=StubExtractionAgent(),
            matching_runner=fake_matching_runner,
            ranking_runner=fake_ranking_runner,
            load_json_fn=fake_load_json,
            save_json_fn=fake_save_json,
        )
        original_run = service.run

        def wrapped_run(*args, **kwargs):
            fake_settings = SimpleNamespace(
                DEMO_OUTPUT_DIR=self.output_dir,
                DEMO_PROFILE_PATH=self.output_dir / "demo_profile.json",
                DEMO_MAX_RESULTS=10,
                DEMO_USE_LIVE_SEARCH=True,
            )
            with patch("services.demo_service.settings", fake_settings):
                return original_run(*args, **kwargs)

        service.run = wrapped_run
        return service


if __name__ == "__main__":
    unittest.main()
