from __future__ import annotations

import json
import re
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
                extracted_scholarships = self.extract_from_page(page_result)
                scholarships.extend(extracted_scholarships)
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
                fallback_scholarship = self._build_fallback_scholarship(page_result)
                if fallback_scholarship is not None:
                    scholarships.append(fallback_scholarship)

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
            "source_acceptance_status": page_result.get("source_acceptance_status"),
            "cleaned_text": str(page_result.get("cleaned_text") or "")[
                : settings.EXTRACTION_TEXT_MAX_CHARS
            ],
        }
        page_json = json.dumps(page_payload, indent=2, ensure_ascii=False)
        return f"{self.prompt_template}\n\nCleaned page content:\n{page_json}"

    def _build_source_metadata(self, page_result: dict) -> dict:
        source_url = page_result.get("url")
        return {
            "source_url": source_url,
            "source_type": page_result.get("source_type"),
            "source_reliability_score": page_result.get("source_reliability_score"),
            "pdf_url": source_url if str(source_url or "").casefold().endswith(".pdf") else None,
        }

    def _build_fallback_scholarship(self, page_result: dict) -> dict | None:
        source_url = str(page_result.get("url") or "").strip()
        title = " ".join(str(page_result.get("title") or "").split())
        cleaned_text = str(page_result.get("cleaned_text") or "")
        if not source_url or not title:
            return None

        official_link = self._extract_useful_link(cleaned_text)
        pdf_url = source_url if source_url.casefold().endswith(".pdf") else ""
        display_link = official_link or source_url or pdf_url
        if not display_link:
            return None

        return {
            "scholarship_name": title,
            "institution": None,
            "country": page_result.get("target_country"),
            "academic_level": None,
            "eligible_nationalities": [],
            "required_languages": [],
            "fields": [],
            "benefits": [],
            "deadline": None,
            "requirements": [],
            "application_status": "unknown",
            "source_url": source_url,
            "official_link": official_link,
            "application_url": official_link,
            "pdf_url": pdf_url,
            "display_link": display_link,
            "source_type": page_result.get("source_type"),
            "source_reliability_score": page_result.get("source_reliability_score"),
            "extraction_confidence": 35,
            "evidence_snippets": [cleaned_text[:500]] if cleaned_text else [],
        }

    def _extract_useful_link(self, cleaned_text: str) -> str:
        for match in re.finditer(r"https?://[^\s)>\"]+", cleaned_text):
            url = match.group(0).rstrip(".,;")
            context_start = max(0, match.start() - 80)
            context_end = min(len(cleaned_text), match.end() + 80)
            context = cleaned_text[context_start:context_end].casefold()
            if any(term in context for term in ("apply", "application", "scholarship", "fellowship")):
                return url
        return ""
