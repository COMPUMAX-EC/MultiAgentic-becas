from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request

from config.settings import settings


class QwenClientError(RuntimeError):
    pass


class QwenClient:
    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.host = (host or settings.OLLAMA_HOST).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout_seconds = timeout_seconds or settings.LLM_TIMEOUT_SECONDS

    def generate(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise QwenClientError("Prompt cannot be empty.")

        request_body = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        request = urllib.request.Request(
            url=f"{self.host}/api/generate",
            data=json.dumps(request_body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                response_body = response.read().decode("utf-8")
        except socket.timeout as exc:
            raise QwenClientError(
                f"Ollama request timed out after {self.timeout_seconds} seconds."
            ) from exc
        except urllib.error.URLError as exc:
            raise QwenClientError(
                f"Could not connect to Ollama at {self.host}. Is Ollama running?"
            ) from exc

        try:
            payload = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise QwenClientError("Ollama returned invalid JSON.") from exc

        if "error" in payload:
            raise QwenClientError(f"Ollama error: {payload['error']}")

        generated_text = payload.get("response")
        if not isinstance(generated_text, str):
            raise QwenClientError("Ollama response did not include generated text.")

        return generated_text.strip()
