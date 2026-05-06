from __future__ import annotations

import json
import socket
import unittest
import urllib.error
from unittest.mock import patch

from llm.remote_client import RemoteLLMClient, RemoteLLMClientError


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class RemoteLLMClientTests(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_successful_remote_response_parsing(self, mock_urlopen) -> None:
        mock_urlopen.return_value = FakeResponse(
            {"choices": [{"message": {"content": "hello from remote"}}]}
        )

        client = RemoteLLMClient(
            base_url="https://example.com/v1",
            model="qwen",
            timeout_seconds=1,
        )

        self.assertEqual(client.generate("Say hello"), "hello from remote")

    def test_missing_remote_base_url_fails_clearly(self) -> None:
        client = RemoteLLMClient(base_url="", timeout_seconds=1)

        with self.assertRaises(RemoteLLMClientError) as context:
            client.generate("test")

        self.assertIn("REMOTE_LLM_BASE_URL", str(context.exception))

    @patch("urllib.request.urlopen")
    def test_http_error_handled_clearly(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://example.com/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )
        client = RemoteLLMClient(
            base_url="https://example.com/v1",
            model="qwen",
            timeout_seconds=1,
        )

        with self.assertRaises(RemoteLLMClientError) as context:
            client.generate("test")

        self.assertIn("HTTP 401", str(context.exception))

    @patch("urllib.request.urlopen")
    def test_timeout_handled_clearly(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = socket.timeout()
        client = RemoteLLMClient(
            base_url="https://example.com/v1",
            model="qwen",
            timeout_seconds=1,
        )

        with self.assertRaises(RemoteLLMClientError) as context:
            client.generate("test")

        self.assertIn("timed out", str(context.exception))

    @patch("urllib.request.urlopen")
    def test_api_key_header_is_added_only_when_provided(self, mock_urlopen) -> None:
        mock_urlopen.return_value = FakeResponse(
            {"choices": [{"message": {"content": "ok"}}]}
        )

        client_with_key = RemoteLLMClient(
            base_url="https://example.com/v1",
            api_key="secret",
            model="qwen",
            timeout_seconds=1,
        )
        client_with_key.generate("test")
        first_request = mock_urlopen.call_args_list[0][0][0]
        self.assertEqual(first_request.headers.get("Authorization"), "Bearer secret")

        client_without_key = RemoteLLMClient(
            base_url="https://example.com/v1",
            api_key="",
            model="qwen",
            timeout_seconds=1,
        )
        client_without_key.generate("test")
        second_request = mock_urlopen.call_args_list[1][0][0]
        self.assertNotIn("Authorization", second_request.headers)


if __name__ == "__main__":
    unittest.main()
