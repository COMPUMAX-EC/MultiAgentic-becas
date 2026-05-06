from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from database.connection import get_connection
from database.repository import init_database, save_scholarships
from services.refresh_service import RefreshService


class RefreshServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "refresh_test.db"
        init_database(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_expired_deadline_is_marked_expired(self) -> None:
        scholarship_hash = self._save_scholarship(
            name="Expired Scholarship",
            deadline="2024-01-01",
            application_status="open",
        )
        result = self._run_refresh()[0]
        row = self._load_scholarship(scholarship_hash)

        self.assertEqual(result["action"], "marked_expired")
        self.assertEqual(row["application_status"], "closed")

    def test_closed_application_status_is_marked_closed(self) -> None:
        scholarship_hash = self._save_scholarship(
            name="Closed Scholarship",
            deadline="2027-01-01",
            application_status="closed",
        )
        result = self._run_refresh(skip_closed=False)[0]
        row = self._load_scholarship(scholarship_hash)

        self.assertEqual(result["action"], "marked_closed")
        self.assertEqual(row["application_status"], "closed")

    def test_unknown_deadline_is_not_marked_expired(self) -> None:
        result = self._run_refresh_with_single(
            deadline=None,
            application_status="unknown",
        )
        self.assertNotEqual(result["action"], "marked_expired")

    def test_recent_scholarship_can_be_skipped(self) -> None:
        self._save_scholarship(
            name="Recent Scholarship",
            deadline="2027-01-01",
            application_status="open",
        )
        result = self._run_refresh(stale_days=7, force_recent=True)[0]
        self.assertEqual(result["action"], "skipped_recent")

    def test_closed_scholarship_can_be_skipped_when_setting_enabled(self) -> None:
        result = self._run_refresh_with_single(
            deadline="2027-01-01",
            application_status="closed",
            skip_closed=True,
        )
        self.assertEqual(result["action"], "skipped_closed")

    def test_refresh_summary_counts_are_correct(self) -> None:
        self._save_scholarship(
            name="Expired Scholarship",
            deadline="2024-01-01",
            application_status="open",
        )
        self._save_scholarship(
            name="Open Scholarship",
            deadline="2027-01-01",
            application_status="open",
        )
        payload = self._run_refresh_payload()
        summary = payload["summary"]

        self.assertEqual(summary["records_checked"], 2)
        self.assertEqual(summary["marked_expired"], 1)
        self.assertEqual(summary["kept_active"], 1)

    def _run_refresh_with_single(
        self,
        deadline: str | None,
        application_status: str,
        skip_closed: bool = False,
    ) -> dict:
        self._save_scholarship(
            name="Single Scholarship",
            deadline=deadline,
            application_status=application_status,
        )
        return self._run_refresh(skip_closed=skip_closed)[0]

    def _run_refresh(
        self,
        stale_days: int = 7,
        skip_closed: bool = False,
        expect_results: bool = True,
        force_recent: bool = False,
    ):
        payload = self._run_refresh_payload(
            stale_days=stale_days,
            skip_closed=skip_closed,
            force_recent=force_recent,
        )
        if expect_results:
            return payload["refresh_results"]
        return payload["summary"]

    def _run_refresh_payload(
        self,
        stale_days: int = 7,
        skip_closed: bool = False,
        force_recent: bool = False,
    ) -> dict:
        fake_settings = SimpleNamespace(
            REFRESH_ENABLED=True,
            REFRESH_MAX_RECORDS=20,
            REFRESH_STALE_DAYS=stale_days,
            REFRESH_CHECK_PAGES=False,
            REFRESH_SKIP_CLOSED=skip_closed,
        )
        with patch("services.refresh_service.settings", fake_settings), patch(
            "services.refresh_service.init_database"
        ) as mock_init_database, patch(
            "services.refresh_service.list_scholarships_for_refresh"
        ) as mock_list_scholarships, patch(
            "services.refresh_service.update_scholarship_refresh_status"
        ) as mock_update_status, patch(
            "services.refresh_service.update_scholarship_last_seen"
        ) as mock_update_last_seen:
            mock_init_database.return_value = None
            mock_list_scholarships.return_value = self._list_rows_for_refresh(
                stale_days=stale_days,
                force_recent=force_recent,
            )
            mock_update_status.side_effect = (
                lambda scholarship_hash, application_status=None, deadline=None: self._apply_status_update(
                    scholarship_hash, application_status, deadline
                )
            )
            mock_update_last_seen.side_effect = (
                lambda scholarship_hash: self._apply_last_seen_update(scholarship_hash)
            )
            return RefreshService().refresh()

    def _save_scholarship(
        self,
        name: str,
        deadline: str | None,
        application_status: str,
    ) -> str:
        scholarship = {
            "scholarship_name": name,
            "institution": "Example University",
            "country": "Canada",
            "academic_level": "Bachelor",
            "eligible_nationalities": ["International students"],
            "required_languages": ["English"],
            "fields": ["Computer Science"],
            "benefits": ["Full tuition"],
            "deadline": deadline,
            "requirements": ["Academic merit"],
            "application_status": application_status,
            "source_url": f"https://example.edu/{name.lower().replace(' ', '-')}",
            "source_type": "official_university",
            "source_reliability_score": 90,
            "extraction_confidence": 85,
            "evidence_snippets": ["Scholarship details"],
        }
        save_scholarships([scholarship], self.db_path)
        connection = get_connection(self.db_path)
        try:
            row = connection.execute(
                "SELECT scholarship_hash FROM scholarships WHERE scholarship_name = ?",
                (name,),
            ).fetchone()
            return row["scholarship_hash"]
        finally:
            connection.close()

    def _list_rows_for_refresh(self, stale_days: int, force_recent: bool) -> list[dict]:
        connection = get_connection(self.db_path)
        try:
            rows = connection.execute(
                "SELECT * FROM scholarships ORDER BY scholarship_name ASC"
            ).fetchall()
            scholarships: list[dict] = []
            for row in rows:
                scholarship = dict(row)
                scholarship["is_stale"] = not force_recent
                scholarships.append(scholarship)
            return scholarships
        finally:
            connection.close()

    def _load_scholarship(self, scholarship_hash: str) -> dict:
        connection = get_connection(self.db_path)
        try:
            row = connection.execute(
                "SELECT * FROM scholarships WHERE scholarship_hash = ?",
                (scholarship_hash,),
            ).fetchone()
            return dict(row)
        finally:
            connection.close()

    def _apply_status_update(
        self,
        scholarship_hash: str,
        application_status: str | None,
        deadline: str | None,
    ) -> None:
        connection = get_connection(self.db_path)
        try:
            connection.execute(
                """
                UPDATE scholarships
                SET application_status = COALESCE(?, application_status),
                    deadline = COALESCE(?, deadline),
                    updated_at = CURRENT_TIMESTAMP,
                    last_seen_at = CURRENT_TIMESTAMP
                WHERE scholarship_hash = ?
                """,
                (application_status, deadline, scholarship_hash),
            )
            connection.commit()
        finally:
            connection.close()

    def _apply_last_seen_update(self, scholarship_hash: str) -> None:
        connection = get_connection(self.db_path)
        try:
            connection.execute(
                """
                UPDATE scholarships
                SET last_seen_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE scholarship_hash = ?
                """,
                (scholarship_hash,),
            )
            connection.commit()
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
