from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import http.client
import urllib.error

from agent.page_reader_agent import PageReaderAgent
from services.cache_service import PageCacheService
from tools.page_reader import PageReadError, read_page


class FakeHTTPResponse:
    def __init__(self, body: str, content_type: str = "text/html") -> None:
        self.body = body
        self.headers = {"Content-Type": content_type}

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return self.body.encode("utf-8")


class PageReaderTests(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_successful_page_read_with_mocked_http_response(self, mock_urlopen) -> None:
        mock_urlopen.return_value = FakeHTTPResponse("<html>Scholarship page</html>")

        self.assertIn("Scholarship page", read_page("https://example.edu/page"))

    @patch("urllib.request.urlopen")
    def test_timeout_or_error_handled_safely(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = urllib.error.URLError("timeout")

        with self.assertRaises(PageReadError):
            read_page("https://example.edu/page")

    def test_rejected_source_skipped(self) -> None:
        result = PageReaderAgent().read_page_source(
            {
                "title": "Rejected",
                "url": "https://example.edu/rejected",
                "source_type": "irrelevant",
                "decision": "reject",
            }
        )

        self.assertEqual(result["status"], "skipped_rejected_source")

    def test_cache_hit_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_service = PageCacheService(cache_dir=Path(temp_dir))
            url = "https://example.edu/cached"
            cache_path = cache_service.save(url, "Cached scholarship text")

            result = PageReaderAgent(cache_service=cache_service).read_page_source(
                {
                    "title": "Cached",
                    "url": url,
                    "source_type": "official_university",
                    "decision": "accept",
                }
            )

        self.assertEqual(result["status"], "cache_hit")
        self.assertEqual(result["cleaned_text"], "Cached scholarship text")
        self.assertEqual(result["cache_path"], str(cache_path))

    @patch("agent.page_reader_agent.read_page")
    def test_accepted_with_warning_source_is_read_and_metadata_preserved(
        self,
        mock_read_page,
    ) -> None:
        mock_read_page.return_value = "<html>Scholarship funding page</html>"
        source = {
            "title": "Verified scholarship article",
            "url": "https://news.example.org/scholarship",
            "source_url": "https://news.example.org/scholarship",
            "original_url": "https://news.example.org/scholarship?ref=search",
            "source_type": "verified_news",
            "decision": "review",
            "acceptance_status": "accepted_with_warning",
            "validation_status": "accepted_with_warning",
            "validation_reason": "Verified informational source.",
            "warnings": ["Verified informational source."],
            "query_used": "verified scholarship news",
            "query_family": "verified_secondary_source",
            "source_family": "verified_secondary_source",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_service = PageCacheService(cache_dir=Path(temp_dir))
            result = PageReaderAgent(cache_service=cache_service).read_page_source(source)

        self.assertEqual(result["status"], "read_success")
        self.assertEqual(result["read_status"], "read_success")
        self.assertEqual(result["source_url"], source["source_url"])
        self.assertEqual(result["original_url"], source["original_url"])
        self.assertEqual(result["validation_status"], "accepted_with_warning")
        self.assertEqual(result["validation_reason"], "Verified informational source.")
        self.assertEqual(result["query_family"], "verified_secondary_source")
        self.assertEqual(result["source_family"], "verified_secondary_source")
        self.assertEqual(result["warnings"], ["Verified informational source."])

    @patch("agent.page_reader_agent.read_page")
    def test_read_failure_records_error_and_preserves_source_url(
        self,
        mock_read_page,
    ) -> None:
        mock_read_page.side_effect = PageReadError("timeout")
        source = {
            "title": "Scholarship page",
            "url": "https://example.edu/scholarship",
            "source_url": "https://example.edu/scholarship",
            "source_type": "university",
            "decision": "accept",
            "validation_status": "accepted",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_service = PageCacheService(cache_dir=Path(temp_dir))
            result = PageReaderAgent(cache_service=cache_service).read_page_source(source)

        self.assertEqual(result["status"], "read_failed")
        self.assertEqual(result["read_status"], "read_failed")
        self.assertEqual(result["read_error"], "timeout")
        self.assertEqual(result["source_url"], source["source_url"])

    @patch("agent.page_reader_agent.read_page")
    def test_remote_disconnected_returns_read_failed_result(
        self,
        mock_read_page,
    ) -> None:
        mock_read_page.side_effect = http.client.RemoteDisconnected(
            "Remote end closed connection without response"
        )
        source = {
            "title": "Scholarship page",
            "url": "https://example.edu/disconnect",
            "source_url": "https://example.edu/disconnect",
            "decision": "accept",
            "validation_status": "accepted",
        }

        result = PageReaderAgent().read_page_source(source)

        self.assertEqual(result["status"], "read_failed")
        self.assertIn("Remote end closed connection", result["read_error"])
        self.assertEqual(result["cleaned_text"], "")

    @patch("agent.page_reader_agent.read_page")
    def test_one_page_failure_does_not_stop_remaining_reads(
        self,
        mock_read_page,
    ) -> None:
        mock_read_page.side_effect = [
            "<html>Scholarship one funding</html>",
            http.client.RemoteDisconnected("Remote end closed connection"),
            "<html>Scholarship three funding</html>",
        ]
        sources = [
            {
                "title": "One",
                "url": "https://example.edu/one",
                "decision": "accept",
                "validation_status": "accepted",
            },
            {
                "title": "Two",
                "url": "https://example.edu/two",
                "decision": "accept",
                "validation_status": "accepted",
            },
            {
                "title": "Three",
                "url": "https://example.edu/three",
                "decision": "accept",
                "validation_status": "accepted",
            },
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_service = PageCacheService(cache_dir=Path(temp_dir))
            results = PageReaderAgent(cache_service=cache_service).read_pages(sources)

        self.assertEqual([result["status"] for result in results], [
            "read_success",
            "read_failed",
            "read_success",
        ])
        self.assertEqual(results[1]["source_url"], "https://example.edu/two")
        self.assertEqual(results[1]["cleaned_text"], "")


if __name__ == "__main__":
    unittest.main()
