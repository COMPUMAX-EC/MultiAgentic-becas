from __future__ import annotations

from config.settings import settings
from llm.gcp_cpu_client import GCPCPUClient, GCPCPUClientError
from llm.qwen_client import QwenClient, QwenClientError
from llm.remote_client import RemoteLLMClient, RemoteLLMClientError


class LLMProviderError(RuntimeError):
    pass


# ── Provider registry ─────────────────────────────────────────────────────────
#
#  LLM_PROVIDER=ollama     → Local Ollama (development / no GPU)
#  LLM_PROVIDER=vllm       → AMD Instinct MI300X via vLLM (hackathon / production GPU)
#  LLM_PROVIDER=remote     → Alias for vllm (legacy)
#  LLM_PROVIDER=gcp_cpu    → GCP VM with CPU-based inference (Ollama / llama.cpp / vLLM-CPU)
#
# Switch with a single env var — no code changes needed.
# ─────────────────────────────────────────────────────────────────────────────


def generate_text(prompt: str) -> str:
    """
    Route the prompt to the configured LLM backend and return the response text.

    Raises LLMProviderError on any backend failure.
    """
    provider = settings.LLM_PROVIDER.strip().lower()

    # ── Local Ollama ──────────────────────────────────────────────────────────
    if provider == "ollama":
        try:
            return QwenClient().generate(prompt)
        except QwenClientError as exc:
            raise LLMProviderError(str(exc)) from exc

    # ── AMD MI300X via vLLM (GPU) ─────────────────────────────────────────────
    if provider in {"remote", "vllm"}:
        try:
            return RemoteLLMClient().generate(prompt)
        except RemoteLLMClientError as exc:
            raise LLMProviderError(str(exc)) from exc

    # ── GCP VM CPU inference ──────────────────────────────────────────────────
    if provider == "gcp_cpu":
        try:
            return GCPCPUClient().generate(prompt)
        except GCPCPUClientError as exc:
            raise LLMProviderError(str(exc)) from exc

    raise LLMProviderError(
        f"Unsupported LLM provider: '{settings.LLM_PROVIDER}'. "
        "Valid values: ollama | vllm | gcp_cpu"
    )
