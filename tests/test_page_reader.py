from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
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


if __name__ == "__main__":
    unittest.main()
