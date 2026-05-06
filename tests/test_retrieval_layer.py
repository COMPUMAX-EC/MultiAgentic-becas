from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from database.repository import init_database, list_recent_scholarships, save_scholarships
from rag.retriever import ScholarshipRetriever


class RetrievalLayerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "retrieval_test.db"
        init_database(self.db_path)
        self.profile = {
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

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_retrieving_scholarships_from_temporary_sqlite_database(self) -> None:
        self._save_sample_scholarships()
        fake_settings = SimpleNamespace(
            RETRIEVAL_MAX_RESULTS=10,
            RETRIEVAL_MIN_SCORE=0,
        )

        with patch("rag.retriever.list_recent_scholarships") as mock_list_recent, patch(
            "rag.retriever.settings", fake_settings
        ):
            mock_list_recent.return_value = list_recent_scholarships(
                limit=10, db_path=self.db_path
            )
            results = ScholarshipRetriever().retrieve(self.profile)

        self.assertGreaterEqual(len(results), 1)

    def test_target_country_match_increases_retrieval_score(self) -> None:
        retriever = ScholarshipRetriever()
        canada_score = retriever._score_scholarship(
            self.profile, self._scholarship(country="Canada", fields=["Computer Science"])
        )["retrieval_score"]
        spain_score = retriever._score_scholarship(
            self.profile, self._scholarship(country="Spain", fields=["Computer Science"])
        )["retrieval_score"]

        self.assertGreater(canada_score, spain_score)

    def test_field_match_increases_retrieval_score(self) -> None:
        retriever = ScholarshipRetriever()
        cs_score = retriever._score_scholarship(
            self.profile, self._scholarship(fields=["Computer Science"])
        )["retrieval_score"]
        history_score = retriever._score_scholarship(
            self.profile, self._scholarship(fields=["History"])
        )["retrieval_score"]

        self.assertGreater(cs_score, history_score)

    def test_closed_scholarship_is_skipped(self) -> None:
        retriever = ScholarshipRetriever()
        self.assertTrue(
            retriever._should_skip(self._scholarship(application_status="closed"))
        )

    def test_retrieval_result_includes_required_fields(self) -> None:
        result = ScholarshipRetriever()._score_scholarship(
            self.profile, self._scholarship()
        )

        for field in (
            "scholarship_name",
            "source_url",
            "institution",
            "country",
            "academic_level",
            "fields",
            "benefits",
            "deadline",
            "application_status",
            "retrieval_score",
            "retrieval_reasons",
            "source_reliability_score",
        ):
            self.assertIn(field, result)

    def test_retrieval_max_results_is_respected(self) -> None:
        fake_settings = SimpleNamespace(
            RETRIEVAL_MAX_RESULTS=1,
            RETRIEVAL_MIN_SCORE=0,
        )
        rows = [
            self._row_from_scholarship(self._scholarship(name="One")),
            self._row_from_scholarship(self._scholarship(name="Two")),
        ]

        with patch("rag.retriever.list_recent_scholarships") as mock_list_recent, patch(
            "rag.retriever.settings", fake_settings
        ):
            mock_list_recent.return_value = rows
            results = ScholarshipRetriever().retrieve(self.profile)

        self.assertEqual(len(results), 1)

    def _save_sample_scholarships(self) -> None:
        save_scholarships(
            [
                {
                    "scholarship_name": "Canada CS Scholarship",
                    "institution": "Example University",
                    "country": "Canada",
                    "academic_level": "Bachelor",
                    "eligible_nationalities": ["International students"],
                    "required_languages": ["English"],
                    "fields": ["Computer Science"],
                    "benefits": ["Full tuition"],
                    "deadline": "2027-01-31",
                    "requirements": ["Academic merit"],
                    "application_status": "open",
                    "source_url": "https://example.edu/canada-cs",
                    "source_type": "official_university",
                    "source_reliability_score": 90,
                    "extraction_confidence": 85,
                    "evidence_snippets": ["For international Computer Science students"],
                },
                {
                    "scholarship_name": "History Scholarship",
                    "institution": "Other University",
                    "country": "Spain",
                    "academic_level": "Bachelor",
                    "eligible_nationalities": ["International students"],
                    "required_languages": ["Spanish"],
                    "fields": ["History"],
                    "benefits": ["Partial funding"],
                    "deadline": "2027-02-15",
                    "requirements": ["Essay"],
                    "application_status": "open",
                    "source_url": "https://example.org/history",
                    "source_type": "official_organization",
                    "source_reliability_score": 75,
                    "extraction_confidence": 80,
                    "evidence_snippets": ["History program funding"],
                },
                {
                    "scholarship_name": "Closed Engineering Scholarship",
                    "institution": "Closed University",
                    "country": "Germany",
                    "academic_level": "Bachelor",
                    "eligible_nationalities": ["International students"],
                    "required_languages": ["English"],
                    "fields": ["Engineering"],
                    "benefits": ["Full tuition"],
                    "deadline": "2027-03-10",
                    "requirements": ["Portfolio"],
                    "application_status": "closed",
                    "source_url": "https://closed.example.edu/eng",
                    "source_type": "official_university",
                    "source_reliability_score": 88,
                    "extraction_confidence": 80,
                    "evidence_snippets": ["Applications closed"],
                },
            ],
            self.db_path,
        )

    def _scholarship(self, **overrides: object) -> dict:
        scholarship = {
            "scholarship_name": "Sample Scholarship",
            "institution": "Example University",
            "country": "Canada",
            "academic_level": "Bachelor",
            "eligible_nationalities": ["International students"],
            "required_languages": ["English"],
            "fields": ["Computer Science"],
            "benefits": ["Full tuition"],
            "deadline": "2027-01-31",
            "requirements": ["Academic merit"],
            "application_status": "open",
            "source_url": "https://example.edu/sample",
            "source_type": "official_university",
            "source_reliability_score": 90,
            "extraction_confidence": 85,
        }
        scholarship.update(overrides)
        return scholarship

    def _row_from_scholarship(self, scholarship: dict) -> dict:
        field_value = scholarship["fields"][0] if scholarship["fields"] else ""
        return {
            "scholarship_name": scholarship["scholarship_name"],
            "institution": scholarship["institution"],
            "country": scholarship["country"],
            "academic_level": scholarship["academic_level"],
            "eligible_nationalities_json": '["International students"]',
            "required_languages_json": '["English"]',
            "fields_json": f'["{field_value}"]',
            "benefits_json": '["Full tuition"]',
            "deadline": scholarship["deadline"],
            "requirements_json": '["Academic merit"]',
            "application_status": scholarship["application_status"],
            "source_url": scholarship["source_url"],
            "source_type": scholarship["source_type"],
            "source_reliability_score": scholarship["source_reliability_score"],
            "extraction_confidence": scholarship["extraction_confidence"],
        }


if __name__ == "__main__":
    unittest.main()
