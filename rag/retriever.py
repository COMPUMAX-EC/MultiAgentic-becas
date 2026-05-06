from __future__ import annotations

import json
from datetime import datetime, timezone

from config.settings import settings
from database.repository import list_recent_scholarships
from rag.vector_store import build_text_for_scholarship, simple_text_similarity
from schemas.retrieval_schema import RetrievalValidationError, build_retrieval_result
from utils.normalizer import (
    normalize_academic_level,
    normalize_country,
    normalize_language_entries,
    normalize_list,
    normalize_text,
)


class ScholarshipRetriever:
    def __init__(self) -> None:
        self.skipped_closed_or_expired = 0

    def retrieve(self, normalized_profile: dict) -> list[dict]:
        recent_scholarships = list_recent_scholarships(
            limit=max(settings.RETRIEVAL_MAX_RESULTS * 5, 20)
        )
        scored_results: list[dict] = []
        self.skipped_closed_or_expired = 0

        for scholarship_row in recent_scholarships:
            scholarship = self._deserialize_scholarship_row(scholarship_row)
            if self._should_skip(scholarship):
                self.skipped_closed_or_expired += 1
                continue

            scored_result = self._score_scholarship(normalized_profile, scholarship)
            if scored_result["retrieval_score"] < settings.RETRIEVAL_MIN_SCORE:
                continue
            scored_results.append(scored_result)

        scored_results.sort(
            key=lambda result: (
                result["retrieval_score"],
                result.get("source_reliability_score", 0),
            ),
            reverse=True,
        )
        return scored_results[: settings.RETRIEVAL_MAX_RESULTS]

    def _score_scholarship(self, normalized_profile: dict, scholarship: dict) -> dict:
        profile_targets = {
            country.casefold()
            for country in normalize_list(normalized_profile.get("target_countries"))
        }
        profile_field = normalize_text(normalized_profile.get("field_of_study")) or ""
        profile_interests = normalize_list(normalized_profile.get("interests"))
        profile_level = normalize_academic_level(normalized_profile.get("academic_level"))
        profile_nationality = normalize_country(normalized_profile.get("nationality"))
        profile_languages = {
            language.casefold()
            for language in normalize_language_entries(normalized_profile.get("languages"))
        }

        scholarship_country = normalize_country(scholarship.get("country"))
        scholarship_level = normalize_academic_level(scholarship.get("academic_level"))
        scholarship_fields = normalize_list(scholarship.get("fields"))
        scholarship_nationalities = normalize_list(
            scholarship.get("eligible_nationalities")
        )
        scholarship_languages = normalize_language_entries(
            scholarship.get("required_languages")
        )

        score = 0
        reasons: list[str] = []

        if scholarship_country and scholarship_country.casefold() in profile_targets:
            score += 25
            reasons.append("Target country aligns with the profile.")

        if self._field_match(profile_field, profile_interests, scholarship_fields):
            score += 25
            reasons.append("Field of study or interests align with the scholarship focus.")

        if profile_level and scholarship_level and profile_level.casefold() == scholarship_level.casefold():
            score += 20
            reasons.append("Academic level matches the scholarship target level.")

        if profile_nationality and self._nationality_match(
            profile_nationality, scholarship_nationalities
        ):
            score += 10
            reasons.append("Nationality appears compatible with eligibility.")

        if scholarship_languages and self._language_match(
            profile_languages, scholarship_languages
        ):
            score += 10
            reasons.append("Language requirements appear compatible.")

        source_reliability = self._clamp_score(scholarship.get("source_reliability_score"))
        reliability_bonus = min(10, source_reliability // 10)
        if reliability_bonus:
            score += reliability_bonus
            reasons.append("Source reliability improves retrieval confidence.")

        profile_text = self._build_profile_text(normalized_profile)
        scholarship_text = build_text_for_scholarship(scholarship)
        semantic_bonus = simple_text_similarity(profile_text, scholarship_text) // 10
        if semantic_bonus:
            score += min(10, semantic_bonus)
            reasons.append("General profile text is similar to the scholarship record.")

        status = str(scholarship.get("application_status") or "unknown").strip().lower()
        if status == "upcoming":
            score += 3
            reasons.append("Application cycle appears upcoming.")
        elif status == "unknown":
            score -= 5
            reasons.append("Application status is uncertain.")

        return build_retrieval_result(
            scholarship_name=scholarship.get("scholarship_name"),
            source_url=scholarship.get("source_url"),
            institution=scholarship.get("institution"),
            country=scholarship.get("country"),
            academic_level=scholarship.get("academic_level"),
            fields=scholarship.get("fields"),
            benefits=scholarship.get("benefits"),
            deadline=scholarship.get("deadline"),
            application_status=scholarship.get("application_status"),
            retrieval_score=score,
            retrieval_reasons=reasons,
            source_reliability_score=source_reliability,
            eligible_nationalities=scholarship.get("eligible_nationalities", []),
            required_languages=scholarship.get("required_languages", []),
            requirements=scholarship.get("requirements", []),
            source_type=scholarship.get("source_type"),
            extraction_confidence=scholarship.get("extraction_confidence"),
        )

    def _deserialize_scholarship_row(self, row: dict) -> dict:
        return {
            "scholarship_name": row.get("scholarship_name"),
            "institution": row.get("institution"),
            "country": row.get("country"),
            "academic_level": row.get("academic_level"),
            "eligible_nationalities": self._load_json_list(
                row.get("eligible_nationalities_json")
            ),
            "required_languages": self._load_json_list(
                row.get("required_languages_json")
            ),
            "fields": self._load_json_list(row.get("fields_json")),
            "benefits": self._load_json_list(row.get("benefits_json")),
            "deadline": row.get("deadline"),
            "requirements": self._load_json_list(row.get("requirements_json")),
            "application_status": row.get("application_status"),
            "source_url": row.get("source_url"),
            "source_type": row.get("source_type"),
            "source_reliability_score": row.get("source_reliability_score"),
            "extraction_confidence": row.get("extraction_confidence"),
        }

    def _load_json_list(self, value: object) -> list[str]:
        if isinstance(value, list):
            return normalize_list(value)
        if not isinstance(value, str) or not value.strip():
            return []
        try:
            loaded_value = json.loads(value)
        except json.JSONDecodeError:
            return []
        return normalize_list(loaded_value)

    def _should_skip(self, scholarship: dict) -> bool:
        status = str(scholarship.get("application_status") or "unknown").strip().lower()
        if status == "closed":
            return True

        deadline_text = normalize_text(scholarship.get("deadline"))
        if not deadline_text:
            return False

        return self._deadline_is_expired(deadline_text)

    def _deadline_is_expired(self, deadline_text: str) -> bool:
        deadline_formats = (
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
        )
        for date_format in deadline_formats:
            try:
                deadline = datetime.strptime(deadline_text, date_format).date()
                return deadline < datetime.now(timezone.utc).date()
            except ValueError:
                continue
        return False

    def _field_match(
        self, profile_field: str, profile_interests: list[str], scholarship_fields: list[str]
    ) -> bool:
        scholarship_text = " ".join(scholarship_fields).casefold()
        if profile_field and profile_field.casefold() in scholarship_text:
            return True
        if any(interest.casefold() in scholarship_text for interest in profile_interests):
            return True
        if profile_field and self._is_stem_related(profile_field) and self._is_stem_related(scholarship_text):
            return True
        return False

    def _nationality_match(
        self, profile_nationality: str, scholarship_nationalities: list[str]
    ) -> bool:
        if not scholarship_nationalities:
            return False
        profile_key = profile_nationality.casefold()
        broad_terms = (
            "international students",
            "all nationalities",
            "all countries",
            "open to all nationalities",
        )
        for nationality in scholarship_nationalities:
            nationality_key = nationality.casefold()
            if nationality_key == profile_key or profile_key in nationality_key:
                return True
            if any(term in nationality_key for term in broad_terms):
                return True
        return False

    def _language_match(
        self, profile_languages: set[str], scholarship_languages: list[str]
    ) -> bool:
        for language in scholarship_languages:
            language_key = language.casefold()
            if any(profile_language in language_key for profile_language in profile_languages):
                return True
        return False

    def _build_profile_text(self, normalized_profile: dict) -> str:
        parts = [
            normalized_profile.get("nationality"),
            normalized_profile.get("country_of_residence"),
            normalized_profile.get("academic_level"),
            normalized_profile.get("field_of_study"),
            " ".join(normalize_list(normalized_profile.get("interests"))),
            " ".join(normalize_list(normalized_profile.get("target_countries"))),
            " ".join(normalize_language_entries(normalized_profile.get("languages"))),
        ]
        return " ".join(str(part).strip() for part in parts if part).strip()

    def _is_stem_related(self, text: str) -> bool:
        stem_terms = (
            "computer",
            "science",
            "data",
            "engineering",
            "technology",
            "artificial intelligence",
            "software",
            "machine learning",
            "statistics",
            "mathematics",
        )
        return any(term in text.casefold() for term in stem_terms)

    def _clamp_score(self, value: object) -> int:
        try:
            score = int(value)
        except (TypeError, ValueError):
            score = 0
        return max(0, min(100, score))
