from __future__ import annotations

import asyncio
from pathlib import Path
import unittest
from unittest.mock import patch

from api.server import app, build_empty_metrics, build_empty_rejection_summary, search_scholarships


class FakeJsonRequest:
    headers = {"content-type": "application/json"}

    def __init__(self, payload: dict) -> None:
        self.payload = payload

    async def json(self) -> dict:
        return self.payload


class SearchInputValidationTests(unittest.TestCase):
    def test_missing_required_fields_stops_before_search(self) -> None:
        with patch(
            "api.server.run_live_search_pipeline",
            side_effect=AssertionError("Search pipeline should not run."),
        ):
            payload = asyncio.run(
                search_scholarships(
                    FakeJsonRequest(
                        {
                            "raw_profile_text": "Quiero una beca para estudiar afuera.",
                            "profile": None,
                        }
                    )
                )
            )

        self.assertEqual(payload["status"], "needs_more_information")
        self.assertIn("country_or_nationality", payload["missing_required_fields"])
        self.assertIn("languages", payload["missing_required_fields"])
        self.assertIn("scholarship_type", payload["missing_required_fields"])
        self.assertEqual(payload["ranked_results"], [])
        self.assertIsNone(payload["search_intent"])
        self.assertIsNone(payload["search_signature"])
        self.assertEqual(payload["metrics"]["generated_queries_count"], 0)
        self.assertEqual(payload["metrics"]["sources_found_count"], 0)
        self.assertEqual(payload["metrics"]["ranked_count"], 0)
        self.assertEqual(
            payload["rejection_summary"]["profile_missing_required_fields"],
            len(payload["missing_required_fields"]),
        )
        steps = {step["step_name"]: step for step in payload["workflow_steps"]}
        self.assertEqual(steps["Searching global sources"]["status"], "skipped")
        self.assertEqual(steps["Ranking recommendations"]["status"], "skipped")

    def test_missing_scholarship_type_stops_before_search(self) -> None:
        with patch(
            "api.server.run_live_search_pipeline",
            side_effect=AssertionError("Search pipeline should not run."),
        ):
            payload = asyncio.run(
                search_scholarships(
                    FakeJsonRequest(
                        {
                            "raw_profile_text": (
                                "Soy ecuatoriano, hablo español e inglés, quiero "
                                "estudiar computer science."
                            ),
                            "profile": None,
                        }
                    )
                )
            )

        self.assertEqual(payload["status"], "needs_more_information")
        self.assertEqual(payload["missing_required_fields"], ["scholarship_type"])
        self.assertEqual(payload["ranked_results"], [])
        self.assertEqual(payload["metrics"]["generated_queries_count"], 0)
        self.assertEqual(
            payload["rejection_summary"]["profile_missing_required_fields"],
            1,
        )

    def test_ecuadorian_written_profile_passes_without_pdf_metadata(self) -> None:
        raw_profile = (
            "I am Ecuadorian and I am studying Information Technology. I speak "
            "Spanish as my native language and English at a B1 level. I am "
            "interested in Cybersecurity, Cloud Computing, Programming, and "
            "Software Development. I am looking for partial or full scholarships "
            "for undergraduate studies, preferably in Spain, Canada, Chile, or "
            "the United States. My budget is limited, and I can contribute up to "
            "5,000 USD per year. I prefer hybrid or on-campus programs."
        )

        with patch("api.server.run_live_search_pipeline", fake_success_pipeline):
            payload = asyncio.run(
                search_scholarships(
                    FakeJsonRequest({"raw_profile_text": raw_profile, "profile": None})
                )
            )

        self.assertNotEqual(payload["status"], "needs_more_information")
        self.assertEqual(
            payload["normalized_profile"]["scholarship_type"],
            "Full or partial funding",
        )
        self.assertEqual(
            payload["search_intent"]["scholarship_type"],
            "Full or partial funding",
        )
        self.assertNotIn("pdf_received", payload)
        self.assertNotIn("pdf_text_extracted", payload)
        self.assertNotIn("pdf_extraction_error", payload)
        self.assertNotIn("cv_text_preview", payload)
        self.assertNotIn("extracted_text_length", payload)
        self.assertNotIn("input_sources", payload["normalized_profile"])

    def test_profile_document_route_is_removed(self) -> None:
        route_paths = {route.path for route in app.routes}

        self.assertNotIn("/search-with-profile-document", route_paths)

    def test_frontend_search_service_no_longer_sends_cv_pdf(self) -> None:
        service_source = Path("services/scholarshipApi.ts").read_text(encoding="utf-8")

        self.assertNotIn("cvPdf", service_source)
        self.assertNotIn("cv_pdf", service_source)
        self.assertNotIn("apiPostFormData", service_source)

    def test_profile_form_uses_backend_search_instead_of_mock_results(self) -> None:
        form_source = Path("components/ProfileForm.tsx").read_text(encoding="utf-8")

        self.assertIn("searchScholarshipsWithProfileInput", form_source)
        self.assertIn("rawProfileText: trimmedProfile", form_source)
        self.assertNotIn("mockScholarships", form_source)


def fake_success_pipeline(normalized_profile: dict, workflow_steps: list[dict]) -> dict:
    return {
        "status": "ok",
        "message": "Fake written-profile pipeline complete.",
        "workflow_steps": workflow_steps,
        "ranked_results": [],
        "recommended": [],
        "less_recommended": [],
        "errors": [],
        "metrics": build_empty_metrics(),
        "rejection_summary": build_empty_rejection_summary(),
    }


if __name__ == "__main__":
    unittest.main()
