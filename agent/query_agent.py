from __future__ import annotations

import json
from pathlib import Path

from config.settings import settings
from llm.provider import LLMProviderError, generate_text
from schemas.search_schema import (
    SearchQueryValidationError,
    validate_generated_queries,
)
from utils.json_handler import JsonHandlerError, parse_json_text


PROMPT_TEMPLATE_PATH = settings.PROJECT_ROOT / "prompts" / "query_generation.txt"


class QueryGenerationError(RuntimeError):
    pass


class QueryAgent:
    def __init__(self, prompt_template_path: Path = PROMPT_TEMPLATE_PATH) -> None:
        self.prompt_template_path = prompt_template_path

    def generate_queries(self, normalized_profile: dict) -> list[dict]:
        prompt = self.build_prompt(normalized_profile)

        try:
            raw_response = generate_text(prompt)
            response_payload = parse_json_text(raw_response)
            raw_queries = response_payload.get("queries")
            return validate_generated_queries(raw_queries)
        except LLMProviderError as exc:
            raise QueryGenerationError(str(exc)) from exc
        except (AttributeError, JsonHandlerError, SearchQueryValidationError) as exc:
            raise QueryGenerationError(f"Could not generate valid queries: {exc}") from exc

    def build_prompt(self, normalized_profile: dict) -> str:
        template = self.prompt_template_path.read_text(encoding="utf-8").strip()
        profile_json = json.dumps(normalized_profile, indent=2, ensure_ascii=False)
        return f"{template}\n\nNormalized profile:\n{profile_json}"
