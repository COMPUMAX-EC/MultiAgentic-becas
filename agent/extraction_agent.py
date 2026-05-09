from __future__ import annotations

import json
import re
from pathlib import Path

from config.settings import settings
from llm.provider import LLMProviderError, generate_text
from schemas.scholarship_schema import (
    ScholarshipValidationError,
    resolve_link_fields,
    validate_scholarship_extractions,
)
from tools.date_validator import has_obvious_expired_signal
from utils.json_handler import JsonHandlerError, parse_json_text
from utils.url_utils import first_useful_url, normalize_useful_url


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

        return self._dedupe_scholarships_by_link_quality(scholarships)

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
            "source_url": page_result.get("source_url") or page_result.get("url"),
            "original_url": page_result.get("original_url"),
            "title": page_result.get("title"),
            "source_type": page_result.get("source_type"),
            "source_decision": page_result.get("source_decision"),
            "source_acceptance_status": page_result.get("source_acceptance_status"),
            "validation_status": page_result.get("validation_status"),
            "validation_reason": page_result.get("validation_reason"),
            "warnings": page_result.get("warnings", []),
            "query_family": page_result.get("query_family"),
            "source_family": page_result.get("source_family"),
            "query_used": page_result.get("query_used"),
            "cleaned_text": str(page_result.get("cleaned_text") or "")[
                : settings.EXTRACTION_TEXT_MAX_CHARS
            ],
        }
        page_json = json.dumps(page_payload, indent=2, ensure_ascii=False)
        return f"{self.prompt_template}\n\nCleaned page content:\n{page_json}"

    def _build_source_metadata(self, page_result: dict) -> dict:
        source_url = first_useful_url(
            page_result.get("source_url"),
            page_result.get("original_url"),
            page_result.get("url"),
        )
        return {
            "source_url": source_url,
            "original_url": normalize_useful_url(page_result.get("original_url")) or source_url,
            "url": normalize_useful_url(page_result.get("url")) or source_url,
            "query_used": page_result.get("query_used"),
            "query_family": page_result.get("query_family"),
            "source_family": page_result.get("source_family"),
            "source_type": page_result.get("source_type"),
            "source_validation_status": page_result.get("validation_status")
            or page_result.get("source_acceptance_status"),
            "source_reliability_score": page_result.get("source_reliability_score"),
            "pdf_url": source_url if str(source_url or "").casefold().endswith(".pdf") else None,
        }

    def _build_fallback_scholarship(self, page_result: dict) -> dict | None:
        source_url = first_useful_url(
            page_result.get("source_url"),
            page_result.get("original_url"),
            page_result.get("url"),
        )
        title = " ".join(str(page_result.get("title") or "").split())
        cleaned_text = str(page_result.get("cleaned_text") or "")
        if not source_url or not title:
            return None

        link_candidates = self._extract_useful_links(cleaned_text)
        official_link = link_candidates.get("official_link", "")
        application_url = link_candidates.get("application_url", "")
        pdf_url = source_url if source_url.casefold().endswith(".pdf") else ""
        if not pdf_url:
            pdf_url = link_candidates.get("pdf_url", "")
        link_fields = resolve_link_fields(
            {
                "official_link": official_link,
                "application_url": application_url,
                "source_url": source_url,
                "pdf_url": pdf_url,
            }
        )
        display_link = link_fields["display_link"]
        if not display_link:
            return None
        deadline_status = (
            "closed"
            if has_obvious_expired_signal(title, cleaned_text[:1000])
            else "unknown"
        )

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
            "deadline_status": deadline_status,
            "requirements": [],
            "application_status": "unknown",
            "source_url": source_url,
            "official_link": link_fields["official_link"],
            "application_url": link_fields["application_url"],
            "pdf_url": link_fields["pdf_url"],
            "display_link": display_link,
            "original_url": normalize_useful_url(page_result.get("original_url")) or source_url,
            "query_used": page_result.get("query_used"),
            "query_family": page_result.get("query_family"),
            "source_family": page_result.get("source_family"),
            "source_type": page_result.get("source_type"),
            "source_validation_status": page_result.get("validation_status")
            or page_result.get("source_acceptance_status"),
            "source_reliability_score": page_result.get("source_reliability_score"),
            "extraction_confidence": 35,
            "evidence_snippets": [cleaned_text[:500]] if cleaned_text else [],
        }

    def _extract_useful_link(self, cleaned_text: str) -> str:
        links = self._extract_useful_links(cleaned_text)
        return first_useful_url(
            links.get("application_url"),
            links.get("official_link"),
            links.get("pdf_url"),
        )

    def _extract_useful_links(self, cleaned_text: str) -> dict[str, str]:
        link_fields = {
            "official_link": "",
            "application_url": "",
            "pdf_url": "",
        }
        for match in re.finditer(r"https?://[^\s)>\"]+", cleaned_text):
            url = normalize_useful_url(match.group(0).rstrip(".,;"))
            if not url:
                continue
            context_start = max(0, match.start() - 80)
            context_end = min(len(cleaned_text), match.end() + 80)
            context = cleaned_text[context_start:context_end].casefold()
            if url.casefold().endswith(".pdf") and not link_fields["pdf_url"]:
                link_fields["pdf_url"] = url
            if (
                not link_fields["application_url"]
                and any(
                    term in context
                    for term in (
                        "apply",
                        "apply now",
                        "application",
                        "aplicar",
                        "postular",
                        "postulación",
                        "postulacion",
                        "formulario",
                    )
                )
            ):
                link_fields["application_url"] = url
            if (
                not link_fields["official_link"]
                and any(
                    term in context
                    for term in (
                        "official call",
                        "call for applications",
                        "scholarship page",
                        "funding opportunity",
                        "convocatoria",
                        "bases de la convocatoria",
                        "scholarship",
                        "fellowship",
                    )
                )
            ):
                link_fields["official_link"] = url
        return link_fields

    def _dedupe_scholarships_by_link_quality(self, scholarships: list[dict]) -> list[dict]:
        best_by_key: dict[str, dict] = {}
        for scholarship in scholarships:
            link_fields = resolve_link_fields(scholarship)
            if not link_fields["display_link"]:
                continue
            normalized_scholarship = {**scholarship, **link_fields}
            key = self._scholarship_key(normalized_scholarship)
            current = best_by_key.get(key)
            if current is None or self._link_quality_key(
                normalized_scholarship
            ) > self._link_quality_key(current):
                best_by_key[key] = normalized_scholarship
        return list(best_by_key.values())

    def _scholarship_key(self, scholarship: dict) -> str:
        name = " ".join(
            str(scholarship.get("scholarship_name") or "").casefold().split()
        )
        source_url = normalize_useful_url(scholarship.get("source_url"))
        if name and source_url:
            return f"name-source:{name}:{source_url}"
        display_link = normalize_useful_url(scholarship.get("display_link"))
        if display_link:
            return f"link:{display_link}"
        return f"name:{name}"

    def _link_quality_key(self, scholarship: dict) -> tuple[int, int]:
        link_fields = resolve_link_fields(scholarship)
        if link_fields["official_link"]:
            link_score = 4
        elif link_fields["application_url"]:
            link_score = 3
        elif link_fields["source_url"]:
            link_score = 2
        elif link_fields["pdf_url"]:
            link_score = 1
        else:
            link_score = 0
        meaningful_fields = (
            "institution",
            "country",
            "academic_level",
            "deadline",
            "benefits",
            "requirements",
            "eligible_nationalities",
            "required_languages",
            "fields",
        )
        completeness = sum(1 for field in meaningful_fields if scholarship.get(field))
        return (link_score, completeness)
