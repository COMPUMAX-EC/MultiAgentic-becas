"""
gcp_cpu_client.py — LLM client for a GCP VM running CPU-based inference.

Supported backends on the GCP VM (all OpenAI-compatible):
  - Ollama  → http://<GCP_IP>:11434/v1   (recommended: easiest setup)
  - llama.cpp server → http://<GCP_IP>:8080/v1
  - vLLM with CPU    → http://<GCP_IP>:8000/v1

This client is a thin, CPU-aware wrapper over the same HTTP logic as
RemoteLLMClient but with:
  - Higher default timeout  (CPU inference is 5-20x slower than GPU)
  - Configurable concurrency hint for llama.cpp (-t flag)
  - Clear error messages that mention GCP/CPU context

Setup on GCP VM (Ubuntu):
  # Option A — Ollama (recommended)
  curl -fsSL https://ollama.com/install.sh | sh
  OLLAMA_HOST=0.0.0.0 ollama serve &
  ollama pull qwen2.5:3b          # or 7b-q4 for better quality on CPU

  # Option B — llama.cpp
  ./server -m qwen2.5-3b-q4.gguf --host 0.0.0.0 --port 8080 -t $(nproc)

  # Firewall
  gcloud compute firewall-rules create allow-llm \\
    --allow tcp:11434,tcp:8080 --source-ranges 0.0.0.0/0
"""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request

from config.settings import settings


class GCPCPUClientError(RuntimeError):
    pass


class GCPCPUClient:
    """
    OpenAI-compatible client targeting a CPU-based LLM on a GCP VM.
    Works with Ollama (/v1/chat/completions), llama.cpp server, or vLLM-CPU.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.base_url = (base_url or settings.GCP_VM_BASE_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.GCP_VM_API_KEY
        self.model = model or settings.GCP_VM_MODEL
        # CPU inference is significantly slower — use dedicated timeout
        self.timeout_seconds = timeout_seconds or settings.GCP_VM_TIMEOUT_SECONDS

    def generate(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise GCPCPUClientError("Prompt cannot be empty.")
        if not self.base_url:
            raise GCPCPUClientError(
                "GCP_VM_BASE_URL is not configured. "
                "Set it to http://<GCP_VM_IP>:<PORT>/v1 in your .env file."
            )

        request_body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 2048,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        request = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=json.dumps(request_body).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as resp:
                response_body = resp.read().decode("utf-8")

        except socket.timeout as exc:
            raise GCPCPUClientError(
                f"GCP CPU VM request timed out after {self.timeout_seconds}s. "
                "CPU inference is slow — try a smaller/quantized model or increase "
                "GCP_VM_TIMEOUT_SECONDS in your .env."
            ) from exc

        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="ignore").strip()
            except Exception:
                pass
            raise GCPCPUClientError(
                f"GCP VM returned HTTP {exc.code}. {body}"
            ) from exc

        except urllib.error.URLError as exc:
            raise GCPCPUClientError(
                f"Could not connect to GCP VM at {self.base_url}. "
                "Check the VM IP, firewall rules, and that the inference server is running."
            ) from exc

        try:
            payload = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise GCPCPUClientError("GCP VM returned invalid JSON.") from exc

        content = self._extract_content(payload)
        if not content:
            raise GCPCPUClientError("GCP VM response did not include generated text.")
        return content.strip()

    def _extract_content(self, payload: dict) -> str | None:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            return None
        content = message.get("content")
        return content if isinstance(content, str) else None
