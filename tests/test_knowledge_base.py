from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from database.connection import get_connection
from database.repository import (
    get_existing_scholarship_by_hash,
    init_database,
    list_recent_scholarships,
    save_profile,
    save_scholarships,
    save_sources,
)
from utils.hash_utils import profile_hash, scholarship_hash


class KnowledgeBaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_scholarships.db"
        init_database(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_database_initialization_creates_tables(self) -> None:
        connection = get_connection(self.db_path)
        try:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        finally:
            connection.close()

        table_names = {row["name"] for row in rows}
        self.assertTrue(
            {"profiles", "search_queries", "sources", "scholarships", "extraction_runs"}
            .issubset(table_names)
        )

    def test_profile_hash_is_stable(self) -> None:
        profile = {
            "nationality": "Colombian",
            "country_of_residence": "Colombia",
            "academic_level": "Bachelor",
            "field_of_study": "Computer Science",
        }
        self.assertEqual(profile_hash(profile), profile_hash(dict(profile)))

    def test_scholarship_hash_is_stable(self) -> None:
        self.assertEqual(
            scholarship_hash("Example Scholarship", "https://example.org"),
            scholarship_hash("Example Scholarship", "https://example.org"),
        )

    def test_saving_duplicate_scholarship_updates_instead_of_duplicating(self) -> None:
        scholarship = {
            "scholarship_name": "Example Scholarship",
            "institution": "Example University",
            "country": "Canada",
            "academic_level": "Bachelor",
            "eligible_nationalities": ["Colombian"],
            "required_languages": ["English"],
            "fields": ["Computer Science"],
            "benefits": ["Partial tuition"],
            "deadline": None,
            "requirements": ["Requirement A"],
            "application_status": "open",
            "source_url": "https://example.edu/scholarship",
            "source_type": "official_university",
            "source_reliability_score": 90,
            "extraction_confidence": 80,
            "evidence_snippets": ["Snippet A"],
        }
        updated_scholarship = dict(scholarship)
        updated_scholarship["benefits"] = ["Full tuition"]

        first_result = save_scholarships([scholarship], self.db_path)
        second_result = save_scholarships([updated_scholarship], self.db_path)

        scholarship_id = scholarship_hash(
            scholarship["scholarship_name"], scholarship["source_url"]
        )
        saved_record = get_existing_scholarship_by_hash(scholarship_id, self.db_path)

        self.assertEqual(first_result["inserted"], 1)
        self.assertEqual(second_result["updated"], 1)
        self.assertIn("Full tuition", saved_record["benefits_json"])

    def test_saving_source_with_same_url_does_not_duplicate(self) -> None:
        source = {
            "url": "https://example.edu/scholarship",
            "title": "Scholarship",
            "snippet": "Funding available",
            "source_type": "official_university",
            "reliability_score": 90,
            "relevance_score": 85,
            "decision": "accept",
        }

        save_sources([source], self.db_path)
        save_sources([source], self.db_path)

        connection = get_connection(self.db_path)
        try:
            count = connection.execute("SELECT COUNT(*) AS count FROM sources").fetchone()[
                "count"
            ]
        finally:
            connection.close()

        self.assertEqual(count, 1)

    def test_list_recent_scholarships_returns_records(self) -> None:
        scholarship = {
            "scholarship_name": "Example Scholarship",
            "institution": "Example University",
            "country": "Canada",
            "academic_level": "Bachelor",
            "eligible_nationalities": [],
            "required_languages": [],
            "fields": [],
            "benefits": [],
            "deadline": None,
            "requirements": [],
            "application_status": "unknown",
            "source_url": "https://example.edu/scholarship",
            "source_type": "official_university",
            "source_reliability_score": 90,
            "extraction_confidence": 80,
            "evidence_snippets": [],
        }
        save_scholarships([scholarship], self.db_path)

        records = list_recent_scholarships(limit=5, db_path=self.db_path)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["scholarship_name"], "Example Scholarship")


if __name__ == "__main__":
    unittest.main()
