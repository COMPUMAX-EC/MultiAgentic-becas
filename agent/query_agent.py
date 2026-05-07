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
        self.prompt_template = self.prompt_template_path.read_text(
            encoding="utf-8"
        ).strip()

    def generate_queries(self, normalized_profile: dict) -> list[dict]:
        prompt = self.build_prompt(normalized_profile)

        try:
            raw_response = generate_text(prompt)
            response_payload = parse_json_text(raw_response)
            raw_queries = response_payload.get("queries")
            llm_queries = validate_generated_queries(raw_queries)
            return validate_generated_queries(
                [*llm_queries, *self.build_deterministic_query_families(normalized_profile)]
            )
        except LLMProviderError as exc:
            return validate_generated_queries(
                self.build_deterministic_query_families(normalized_profile)
            )
        except (AttributeError, JsonHandlerError, SearchQueryValidationError) as exc:
            raise QueryGenerationError(f"Could not generate valid queries: {exc}") from exc

    def build_prompt(self, normalized_profile: dict) -> str:
        profile_json = json.dumps(normalized_profile, indent=2, ensure_ascii=False)
        return f"{self.prompt_template}\n\nNormalized profile:\n{profile_json}"

    def build_deterministic_query_families(self, normalized_profile: dict) -> list[dict]:
        nationality = self._text(normalized_profile.get("nationality")) or "international"
        academic_level = self._text(normalized_profile.get("academic_level")) or "students"
        field = self._field_text(normalized_profile)
        scholarship_type = self._text(normalized_profile.get("scholarship_type")) or "scholarships"
        languages = self._languages_text(normalized_profile.get("languages"))
        target_countries = self._target_countries(normalized_profile)

        query_templates = [
            (
                "official scholarships for {nationality} students {academic_level} {field}",
                "Find official scholarship pages by nationality, level, and field.",
            ),
            (
                "{scholarship_type} scholarships {field} {country}",
                "Target funding type, field, and destination country.",
            ),
            (
                "site:.edu scholarships international students {field} {academic_level}",
                "Search official university scholarship pages.",
            ),
            (
                "site:.gov scholarships {nationality} students {academic_level}",
                "Search government scholarship pages.",
            ),
            (
                "site:.org scholarships {field} international students",
                "Search organization and foundation scholarship pages.",
            ),
            (
                "university scholarships {country} {field} international students",
                "Search university scholarship pages by target country.",
            ),
            (
                "government scholarships {country} {nationality} students",
                "Search government scholarship programs by destination and nationality.",
            ),
            (
                "company scholarships {field} students international",
                "Search company scholarship and fellowship programs.",
            ),
            (
                "verified scholarship news {field} {country}",
                "Search verified news reports that clearly reference scholarships.",
            ),
            (
                "foundation scholarships {field} {academic_level} international students",
                "Search foundation scholarship opportunities.",
            ),
            (
                "official PDF scholarship announcement {field} {country}",
                "Search official PDF scholarship announcements.",
            ),
        ]

        queries: list[dict] = []
        priority = 1
        for country in target_countries:
            for template, reason in query_templates:
                query = template.format(
                    nationality=nationality,
                    academic_level=academic_level,
                    field=field,
                    scholarship_type=scholarship_type,
                    country=country,
                    languages=languages,
                )
                if languages:
                    query = f"{query} {languages}"
                queries.append(
                    {
                        "query": query,
                        "target_country": country,
                        "reason": reason,
                        "priority": priority,
                    }
                )
                priority += 1

        return queries

    def _field_text(self, normalized_profile: dict) -> str:
        interests = normalized_profile.get("interests")
        if isinstance(interests, list) and interests:
            fields = [self._text(value) for value in interests[:2]]
            return " ".join(value for value in fields if value)
        return self._text(normalized_profile.get("field_of_study")) or "all fields"

    def _languages_text(self, languages: object) -> str:
        if not isinstance(languages, list):
            return ""

        language_names: list[str] = []
        for language_entry in languages:
            if isinstance(language_entry, dict):
                language_name = self._text(language_entry.get("language"))
            else:
                language_name = self._text(language_entry)
            if language_name:
                language_names.append(language_name)

        return " ".join(language_names[:2])

    def _target_countries(self, normalized_profile: dict) -> list[str]:
        countries = normalized_profile.get("target_countries")
        if isinstance(countries, list):
            cleaned_countries = [self._text(country) for country in countries]
            cleaned_countries = [country for country in cleaned_countries if country]
            if cleaned_countries:
                return cleaned_countries[:4]
        return ["global"]

    def _text(self, value: object) -> str:
        return " ".join(str(value or "").strip().split())
