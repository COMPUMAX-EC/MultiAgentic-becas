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
            deterministic_queries = self.build_deterministic_query_families(
                normalized_profile
            )
            raw_response = generate_text(prompt)
            response_payload = parse_json_text(raw_response)
            raw_queries = response_payload.get("queries")
            llm_queries = validate_generated_queries(raw_queries)
            return validate_generated_queries(
                [*deterministic_queries, *llm_queries],
                max_queries=settings.SEARCH_MAX_QUERIES,
            )
        except LLMProviderError as exc:
            return validate_generated_queries(
                self.build_deterministic_query_families(normalized_profile),
                max_queries=settings.SEARCH_MAX_QUERIES,
            )
        except (AttributeError, JsonHandlerError, SearchQueryValidationError) as exc:
            raise QueryGenerationError(f"Could not generate valid queries: {exc}") from exc

    def build_prompt(self, normalized_profile: dict) -> str:
        profile_json = json.dumps(normalized_profile, indent=2, ensure_ascii=False)
        return f"{self.prompt_template}\n\nNormalized profile:\n{profile_json}"

    def build_deterministic_query_families(self, normalized_profile: dict) -> list[dict]:
        nationality = (
            self._text(
                normalized_profile.get("country_of_origin")
                or normalized_profile.get("nationality")
            )
            or "international"
        )
        academic_level = self._academic_level_text(normalized_profile)
        field = self._field_text(normalized_profile)
        scholarship_type = self._scholarship_type_text(normalized_profile)
        languages = self._languages_text(normalized_profile.get("languages"))
        target_countries = self._target_countries(normalized_profile)
        modality = self._explicit_modality_text(normalized_profile)
        budget_terms = self._budget_terms(normalized_profile)

        queries: list[dict] = []
        priority = 1
        for country, template, reason in self._expanded_query_templates(target_countries):
            query = template.format(
                    nationality=nationality,
                    academic_level=academic_level,
                    field=field,
                    scholarship_type=scholarship_type,
                    country=country,
                    languages=languages,
                    country_tld=self._country_tld(country),
                    budget_terms=budget_terms,
                )
            query = self._compact_query(query)
            if languages:
                query = self._compact_query(f"{query} {languages}")
            queries.append(
                {
                    "query": query,
                    "target_country": country,
                    "reason": reason,
                    "priority": priority,
                }
            )
            priority += 1

        if modality:
            for country in target_countries:
                queries.append(
                    {
                        "query": self._compact_query(
                            f"{modality} scholarships {field} {academic_level} {country}"
                        ),
                        "target_country": country,
                        "reason": "Search explicitly requested modality opportunities.",
                        "priority": priority,
                    }
                )
                priority += 1

        return queries

    def _expanded_query_templates(
        self,
        target_countries: list[str],
    ) -> list[tuple[str, str, str]]:
        templates = [
            (
                "{nationality} students {academic_level} scholarship {field} {scholarship_type}",
                "General profile match by nationality, level, field, and funding type.",
            ),
            (
                "international students {academic_level} scholarship {field} {country}",
                "General international student scholarship match by target country.",
            ),
            (
                "{country} government scholarships {nationality} students {academic_level} {field}",
                "Search government scholarship programs by origin, level, and field.",
            ),
            (
                "university scholarships international students {field} {academic_level} {country} site:.edu",
                "Search university scholarship pages by field, level, and target country.",
            ),
            (
                "site:edu.{country_tld} scholarships international students {field} {academic_level}",
                "Search country-specific university education domains.",
            ),
            (
                "foundation scholarships organization scholarships {nationality} students {field} {academic_level}",
                "Search organization and foundation scholarship opportunities.",
            ),
            (
                "research institute scholarships {field} {academic_level} international students",
                "Search institute and research center scholarships.",
            ),
            (
                "technology company scholarships research fellowship {field} students international",
                "Search company scholarships and research fellowship opportunities.",
            ),
            (
                "international organization scholarships {nationality} students {academic_level} {country}",
                "Search international organization scholarships.",
            ),
            (
                "verified scholarship news {field} {country} international students",
                "Search verified informational sources reporting scholarship calls.",
            ),
            (
                "scholarship call {field} {academic_level} {country} {budget_terms}",
                "Search financial-need and funding-aware scholarship opportunities.",
            ),
        ]

        expanded_templates: list[tuple[str, str, str]] = []
        for template, reason in templates:
            for country in target_countries:
                expanded_templates.append((country, template, reason))
        return expanded_templates

    def _field_text(self, normalized_profile: dict) -> str:
        specialization = self._text(normalized_profile.get("specialization"))
        field_of_study = self._text(normalized_profile.get("field_of_study"))
        if specialization and field_of_study and specialization.casefold() not in field_of_study.casefold():
            return f"{field_of_study} {specialization}"
        if specialization:
            return specialization

        interests = normalized_profile.get("interests")
        if isinstance(interests, list) and interests:
            fields = [self._text(value) for value in interests[:2]]
            return " ".join(value for value in fields if value)
        return field_of_study or "all fields"

    def _academic_level_text(self, normalized_profile: dict) -> str:
        academic_level = self._text(normalized_profile.get("academic_level"))
        if not academic_level or academic_level.casefold() in {
            "unspecified",
            "unknown",
            "not specified",
        }:
            return "students"
        return academic_level

    def _scholarship_type_text(self, normalized_profile: dict) -> str:
        scholarship_type = self._text(normalized_profile.get("scholarship_type"))
        if not scholarship_type or scholarship_type.casefold() in {
            "unspecified funding",
            "unknown",
            "not specified",
        }:
            return "scholarship"
        return scholarship_type

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

        language_names = [
            language_name
            for language_name in language_names
            if language_name.casefold() not in {"not specified", "unknown"}
        ]
        return " ".join(language_names[:2])

    def _target_countries(self, normalized_profile: dict) -> list[str]:
        countries = normalized_profile.get("target_countries")
        if isinstance(countries, list):
            cleaned_countries = [self._text(country) for country in countries]
            cleaned_countries = [
                country
                for country in cleaned_countries
                if country and country.casefold() not in {"any", "unknown", "not specified"}
            ]
            if cleaned_countries:
                return cleaned_countries[:4]
        return ["global"]

    def _explicit_modality_text(self, normalized_profile: dict) -> str:
        modality = self._text(normalized_profile.get("preferred_modality"))
        if modality.casefold() in {
            "",
            "any",
            "no preference",
            "not specified",
            "unknown",
        }:
            return ""
        return modality

    def _budget_terms(self, normalized_profile: dict) -> str:
        scholarship_type = self._scholarship_type_text(normalized_profile)
        budget = normalized_profile.get("budget")
        if scholarship_type.casefold() in {"full funding", "fully funded"}:
            return "fully funded financial need"
        if isinstance(budget, dict):
            contribution = budget.get("max_personal_contribution")
            if contribution in (None, ""):
                return scholarship_type
            try:
                if float(contribution) <= 5000:
                    return "financial need"
            except (TypeError, ValueError):
                pass
        return scholarship_type

    def _country_tld(self, country: str) -> str:
        country_tlds = {
            "Canada": "ca",
            "Germany": "de",
            "France": "fr",
            "Spain": "es",
            "United Kingdom": "uk",
            "Netherlands": "nl",
            "Australia": "au",
            "Brazil": "br",
            "Colombia": "co",
            "Mexico": "mx",
            "global": "org",
        }
        return country_tlds.get(country, "org")

    def _compact_query(self, query: str) -> str:
        return " ".join(query.split())

    def _text(self, value: object) -> str:
        return " ".join(str(value or "").strip().split())
