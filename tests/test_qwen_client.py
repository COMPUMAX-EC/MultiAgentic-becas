from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from llm.qwen_client import QwenClient, QwenClientError


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class QwenClientTests(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_generate_returns_plain_text(self, mock_urlopen) -> None:
        mock_urlopen.return_value = FakeResponse({"response": "hello"})

        client = QwenClient(
            host="http://localhost:11434",
            model="qwen2.5:7b-instruct",
            timeout_seconds=1,
        )

        self.assertEqual(client.generate("Say hello"), "hello")

    def test_generate_rejects_empty_prompt(self) -> None:
        client = QwenClient(timeout_seconds=1)

        with self.assertRaises(QwenClientError):
            client.generate("   ")


if __name__ == "__main__":
    unittest.main()
