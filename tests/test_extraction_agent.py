from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from agent.extraction_agent import ExtractionAgent


class ExtractionAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.page_result = {
            "url": "https://example.edu/scholarship",
            "title": "Scholarship page",
            "source_type": "official_university",
            "source_decision": "accept",
            "source_reliability_score": 90,
            "status": "read_success",
            "cleaned_text": "The Example Scholarship supports Computer Science students.",
        }

    @patch("agent.extraction_agent.generate_text")
    def test_parses_valid_mocked_qwen_json_output(self, mock_generate_text) -> None:
        mock_generate_text.return_value = json.dumps(
            {
                "scholarships": [
                    {
                        "scholarship_name": "Example Scholarship",
                        "institution": "Example University",
                        "country": "Canada",
                        "academic_level": "Bachelor",
                        "eligible_nationalities": ["Colombian"],
                        "required_languages": ["English"],
                        "fields": ["Computer Science"],
                        "benefits": ["Partial tuition"],
                        "deadline": None,
                        "requirements": ["Good academic standing"],
                        "application_status": "open",
                        "extraction_confidence": 85,
                        "evidence_snippets": ["supports Computer Science students"],
                    }
                ]
            }
        )

        scholarships = ExtractionAgent().extract_scholarships([self.page_result])

        self.assertEqual(len(scholarships), 1)
        self.assertEqual(scholarships[0]["scholarship_name"], "Example Scholarship")

    @patch("agent.extraction_agent.generate_text")
    def test_rejects_empty_scholarship_extraction(self, mock_generate_text) -> None:
        mock_generate_text.return_value = json.dumps({"scholarships": []})

        agent = ExtractionAgent()
        scholarships = agent.extract_scholarships([self.page_result])

        self.assertEqual(scholarships, [])
        self.assertEqual(len(agent.extraction_errors), 1)

    @patch("agent.extraction_agent.generate_text")
    def test_preserves_source_metadata(self, mock_generate_text) -> None:
        mock_generate_text.return_value = json.dumps(
            {
                "scholarships": [
                    {
                        "scholarship_name": "Metadata Scholarship",
                        "extraction_confidence": 90,
                        "application_status": "unknown",
                        "evidence_snippets": ["Scholarship"],
                    }
                ]
            }
        )

        scholarships = ExtractionAgent().extract_scholarships([self.page_result])

        self.assertEqual(scholarships[0]["source_url"], self.page_result["url"])
        self.assertEqual(scholarships[0]["source_type"], "official_university")
        self.assertEqual(scholarships[0]["source_reliability_score"], 90)

    @patch("agent.extraction_agent.generate_text")
    def test_handles_invalid_qwen_json_safely(self, mock_generate_text) -> None:
        mock_generate_text.return_value = "not json"

        agent = ExtractionAgent()
        scholarships = agent.extract_scholarships([self.page_result])

        self.assertEqual(scholarships, [])
        self.assertEqual(len(agent.extraction_errors), 1)

    @patch("agent.extraction_agent.generate_text")
    def test_supports_multiple_scholarships_from_one_page(self, mock_generate_text) -> None:
        mock_generate_text.return_value = json.dumps(
            {
                "scholarships": [
                    {
                        "scholarship_name": "Scholarship One",
                        "extraction_confidence": 80,
                        "application_status": "open",
                        "evidence_snippets": ["Scholarship One"],
                    },
                    {
                        "scholarship_name": "Scholarship Two",
                        "extraction_confidence": 75,
                        "application_status": "upcoming",
                        "evidence_snippets": ["Scholarship Two"],
                    },
                ]
            }
        )

        scholarships = ExtractionAgent().extract_scholarships([self.page_result])

        self.assertEqual(len(scholarships), 2)


if __name__ == "__main__":
    unittest.main()
