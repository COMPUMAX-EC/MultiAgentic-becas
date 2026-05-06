from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from llm.provider import LLMProviderError, generate_text


class LLMProviderTests(unittest.TestCase):
    @patch("llm.provider.QwenClient")
    def test_ollama_provider_selection(self, mock_qwen_client) -> None:
        mock_qwen_client.return_value.generate.return_value = "ollama response"

        with patch("llm.provider.settings", SimpleNamespace(LLM_PROVIDER="ollama")):
            response = generate_text("test")

        self.assertEqual(response, "ollama response")

    @patch("llm.provider.RemoteLLMClient")
    def test_remote_provider_selection(self, mock_remote_client) -> None:
        mock_remote_client.return_value.generate.return_value = "remote response"

        with patch("llm.provider.settings", SimpleNamespace(LLM_PROVIDER="remote")):
            response = generate_text("test")

        self.assertEqual(response, "remote response")

    @patch("llm.provider.RemoteLLMClient")
    def test_vllm_provider_selection(self, mock_remote_client) -> None:
        mock_remote_client.return_value.generate.return_value = "vllm response"

        with patch("llm.provider.settings", SimpleNamespace(LLM_PROVIDER="vllm")):
            response = generate_text("test")

        self.assertEqual(response, "vllm response")

    def test_unsupported_provider_error(self) -> None:
        with patch("llm.provider.settings", SimpleNamespace(LLM_PROVIDER="unknown")):
            with self.assertRaises(LLMProviderError) as context:
                generate_text("test")

        self.assertIn("Unsupported LLM provider", str(context.exception))


if __name__ == "__main__":
    unittest.main()
