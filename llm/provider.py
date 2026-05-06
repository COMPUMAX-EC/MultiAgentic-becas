from __future__ import annotations

from config.settings import settings
from llm.qwen_client import QwenClient, QwenClientError
from llm.remote_client import RemoteLLMClient, RemoteLLMClientError


class LLMProviderError(RuntimeError):
    pass


def generate_text(prompt: str) -> str:
    provider = settings.LLM_PROVIDER.strip().lower()

    if provider == "ollama":
        try:
            return QwenClient().generate(prompt)
        except QwenClientError as exc:
            raise LLMProviderError(str(exc)) from exc

    if provider in {"remote", "vllm"}:
        try:
            return RemoteLLMClient().generate(prompt)
        except RemoteLLMClientError as exc:
            raise LLMProviderError(str(exc)) from exc

    raise LLMProviderError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")
