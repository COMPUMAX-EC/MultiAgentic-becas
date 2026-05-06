from __future__ import annotations

import json
from pathlib import Path

from config.settings import settings
from llm.provider import LLMProviderError, generate_text
from schemas.scholarship_schema import (
    ScholarshipValidationError,
    validate_scholarship_extractions,
)
from utils.json_handler import JsonHandlerError, parse_json_text


PROMPT_TEMPLATE_PATH = settings.PROJECT_ROOT / "prompts" / "extraction.txt"


class ExtractionAgent:
    def __init__(self, prompt_template_path: Path = PROMPT_TEMPLATE_PATH) -> None:
        self.prompt_template_path = prompt_template_path
        self.prompt_template = self.prompt_template_path.read_text(
            encoding="utf-8"
        ).strip()
        self.extraction_errors: list[dict] = []

    def extract_scholarships(self, page_results: list[dict]) -> list[dict]:
        self.extraction_errors = []
        scholarships: list[dict] = []
        eligible_pages = [
            page
            for page in page_results
            if page.get("cleaned_text") and page.get("status") in {"read_success", "cache_hit"}
        ]

        for page_result in eligible_pages[: settings.EXTRACTION_MAX_PAGES]:
            try:
                scholarships.extend(self.extract_from_page(page_result))
            except (
                LLMProviderError,
                JsonHandlerError,
                ScholarshipValidationError,
                AttributeError,
                TypeError,
                ValueError,
            ) as exc:
                self.extraction_errors.append(
                    {
                        "url": page_result.get("url"),
                        "title": page_result.get("title"),
                        "error": str(exc),
                    }
                )

        return scholarships

    def extract_from_page(self, page_result: dict) -> list[dict]:
        prompt = self.build_prompt(page_result)
        raw_response = generate_text(prompt)
        response_payload = parse_json_text(raw_response)
        raw_scholarships = response_payload.get("scholarships")

        return validate_scholarship_extractions(
            raw_scholarships,
            self._build_source_metadata(page_result),
            min_confidence=settings.EXTRACTION_MIN_CONFIDENCE,
        )

    def build_prompt(self, page_result: dict) -> str:
        page_payload = {
            "url": page_result.get("url"),
            "title": page_result.get("title"),
            "source_type": page_result.get("source_type"),
            "source_decision": page_result.get("source_decision"),
            "cleaned_text": str(page_result.get("cleaned_text") or "")[
                : settings.EXTRACTION_TEXT_MAX_CHARS
            ],
        }
        page_json = json.dumps(page_payload, indent=2, ensure_ascii=False)
        return f"{self.prompt_template}\n\nCleaned page content:\n{page_json}"

    def _build_source_metadata(self, page_result: dict) -> dict:
        return {
            "source_url": page_result.get("url"),
            "source_type": page_result.get("source_type"),
            "source_reliability_score": page_result.get("source_reliability_score"),
        }
