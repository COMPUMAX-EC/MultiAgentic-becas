from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request

from config.settings import settings


class RemoteLLMClientError(RuntimeError):
    pass


class RemoteLLMClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        endpoint_type: str | None = None,
    ) -> None:
        self.base_url = (base_url or settings.REMOTE_LLM_BASE_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.REMOTE_LLM_API_KEY
        self.model = model or settings.REMOTE_LLM_MODEL
        self.timeout_seconds = timeout_seconds or settings.REMOTE_LLM_TIMEOUT_SECONDS
        self.endpoint_type = (
            endpoint_type or settings.REMOTE_LLM_ENDPOINT_TYPE
        ).strip().lower()

    def generate(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise RemoteLLMClientError("Prompt cannot be empty.")
        if not self.base_url:
            raise RemoteLLMClientError("REMOTE_LLM_BASE_URL is not configured.")
        if self.endpoint_type != "openai_compatible":
            raise RemoteLLMClientError(
                f"Unsupported remote endpoint type: {self.endpoint_type}"
            )

        request_body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
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
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                response_body = response.read().decode("utf-8")
        except socket.timeout as exc:
            raise RemoteLLMClientError(
                f"Remote LLM request timed out after {self.timeout_seconds} seconds."
            ) from exc
        except urllib.error.HTTPError as exc:
            error_body = ""
            try:
                error_body = exc.read().decode("utf-8", errors="ignore").strip()
            except Exception:
                error_body = ""
            detail = f" HTTP {exc.code}."
            if error_body:
                detail += f" {error_body}"
            raise RemoteLLMClientError(f"Remote LLM request failed.{detail}") from exc
        except urllib.error.URLError as exc:
            raise RemoteLLMClientError(
                f"Could not connect to remote LLM endpoint at {self.base_url}."
            ) from exc

        try:
            payload = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise RemoteLLMClientError("Remote LLM returned invalid JSON.") from exc

        generated_text = self._extract_content(payload)
        if not generated_text:
            raise RemoteLLMClientError(
                "Remote LLM response did not include generated text."
            )
        return generated_text.strip()

    def _extract_content(self, payload: dict) -> str | None:
        if not isinstance(payload, dict):
            return None

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return None

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return None

        message = first_choice.get("message")
        if not isinstance(message, dict):
            return None

        content = message.get("content")
        if isinstance(content, str):
            return content
        return None
