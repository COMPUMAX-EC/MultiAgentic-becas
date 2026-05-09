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
REQUIRED_QUERY_FAMILIES = (
    "destination",
    "nationality",
    "field",
    "academic_level",
    "scholarship_type",
    "university",
    "government",
    "embassy",
    "international_organization",
    "foundation",
    "company",
    "professional_association",
    "verified_secondary_source",
)


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
        search_intent = self._search_intent(normalized_profile)
        search_intent_json = json.dumps(search_intent, indent=2, ensure_ascii=False)
        return (
            f"{self.prompt_template}\n\n"
            f"Search intent:\n{search_intent_json}\n\n"
            f"Normalized profile:\n{profile_json}"
        )

    def build_deterministic_query_families(self, normalized_profile: dict) -> list[dict]:
        intent = self._search_intent(normalized_profile)
        nationality = self._country_or_nationality_text(intent)
        academic_level = self._academic_level_text(intent)
        field = self._field_text(intent)
        scholarship_type = self._scholarship_type_text(intent)
        languages = self._languages_text(intent.get("languages"))
        target_countries = self._target_countries(intent)
        modality = self._explicit_modality_text(intent)
        budget_terms = self._budget_terms(intent)
        search_specificity = self._text(intent.get("search_specificity")) or "moderate"

        queries: list[dict] = []
        for country, template in self._expanded_query_templates(
            target_countries,
            search_specificity,
        ):
            optional_values = {
                "academic_level": academic_level,
                "field": field,
                "languages": languages,
                "modality": modality,
                "budget_terms": budget_terms,
                "country": "" if country == "global" else country,
            }
            query = self._format_query(
                template["template"],
                {
                    "nationality": nationality,
                    "academic_level": academic_level,
                    "field": field,
                    "scholarship_type": scholarship_type,
                    "country": "" if country == "global" else country,
                    "languages": languages,
                    "country_tld": self._country_tld(country),
                    "budget_terms": budget_terms,
                    "modality": modality,
                },
                optional_values,
            )
            if not query:
                continue
            queries.append(
                {
                    "query": query,
                    "target_country": country,
                    "reason": template["reason"],
                    "query_family": template["query_family"],
                    "source_family": template["source_family"],
                    "expansion_round": template["expansion_round"],
                    "priority": len(queries) + 1,
                }
            )

        if modality:
            for country in target_countries:
                queries.append(
                    {
                        "query": self._compact_query(
                            " ".join(
                                value
                                for value in (
                                    modality,
                                    "scholarships",
                                    field,
                                    academic_level,
                                    country if country != "global" else "",
                                )
                                if value
                            )
                        ),
                        "target_country": country,
                        "reason": "Search explicitly requested modality opportunities.",
                        "query_family": "destination",
                        "source_family": "unknown",
                        "expansion_round": 0,
                        "priority": len(queries) + 1,
                    }
                )

        return queries

    def _expanded_query_templates(
        self,
        target_countries: list[str],
        search_specificity: str,
    ) -> list[tuple[str, dict]]:
        base_round = 0
        exact_round = 0 if search_specificity == "specific" else 1
        source_round = 1 if search_specificity == "specific" else 0
        broad_round = 2

        templates: list[dict] = [
            {
                "query_family": "destination",
                "source_family": "unknown",
                "expansion_round": base_round,
                "template": "{nationality} students {scholarship_type} {academic_level?} scholarship {field?} {country?}",
                "reason": "Search exact destination-aware scholarship matches.",
            },
            {
                "query_family": "nationality",
                "source_family": "unknown",
                "expansion_round": base_round,
                "template": "{nationality} students {scholarship_type} scholarships {academic_level?} {field?} {languages?}",
                "reason": "Search by applicant origin and funding type.",
            },
            {
                "query_family": "field",
                "source_family": "unknown",
                "expansion_round": exact_round,
                "template": "{field?} scholarships {nationality} students {scholarship_type} {academic_level?} {country?}",
                "reason": "Search by field or specialization when provided.",
            },
            {
                "query_family": "academic_level",
                "source_family": "unknown",
                "expansion_round": exact_round,
                "template": "{academic_level?} scholarships {nationality} students {scholarship_type} {field?} {country?}",
                "reason": "Search by academic level when provided.",
            },
            {
                "query_family": "scholarship_type",
                "source_family": "unknown",
                "expansion_round": base_round,
                "template": "{scholarship_type} scholarships {nationality} students {academic_level?} {field?} {country?}",
                "reason": "Search by requested funding type.",
            },
            {
                "query_family": "university",
                "source_family": "university",
                "expansion_round": source_round,
                "template": "{country?} university scholarships international students {field?} {academic_level?} site:.edu",
                "reason": "Search university scholarship pages.",
            },
            {
                "query_family": "government",
                "source_family": "government",
                "expansion_round": source_round,
                "template": "{country?} government scholarships {nationality} students {academic_level?} {field?}",
                "reason": "Search government scholarship programs.",
            },
            {
                "query_family": "field",
                "source_family": "unknown",
                "expansion_round": source_round,
                "template": "research institute scholarships {field?} {academic_level?} international students {country?}",
                "reason": "Search research institute scholarship and fellowship pages.",
            },
            {
                "query_family": "embassy",
                "source_family": "embassy",
                "expansion_round": source_round,
                "template": "embassy scholarships {nationality} students {country?} postgraduate {field?}",
                "reason": "Search embassy scholarship announcements.",
            },
            {
                "query_family": "international_organization",
                "source_family": "international_organization",
                "expansion_round": broad_round,
                "template": "international organization scholarships {nationality} students {academic_level?} {field?} {country?}",
                "reason": "Search international organization scholarship programs.",
            },
            {
                "query_family": "foundation",
                "source_family": "foundation",
                "expansion_round": broad_round,
                "template": "foundation scholarships {nationality} students {field?} {academic_level?} {scholarship_type}",
                "reason": "Search foundation-funded opportunities.",
            },
            {
                "query_family": "company",
                "source_family": "company",
                "expansion_round": broad_round,
                "template": "company scholarships {field?} students {country?} {academic_level?}",
                "reason": "Search company scholarship and fellowship opportunities.",
            },
            {
                "query_family": "professional_association",
                "source_family": "professional_association",
                "expansion_round": broad_round,
                "template": "professional association scholarships {field?} students {academic_level?} {country?}",
                "reason": "Search professional association scholarships.",
            },
            {
                "query_family": "verified_secondary_source",
                "source_family": "verified_secondary_source",
                "expansion_round": broad_round,
                "template": "verified scholarship news {nationality} students {field?} {country?} {academic_level?}",
                "reason": "Search verified secondary sources that report scholarship calls.",
            },
            {
                "query_family": "scholarship_type",
                "source_family": "unknown",
                "expansion_round": broad_round,
                "template": "scholarship call {field?} {academic_level?} {country?} {budget_terms?}",
                "reason": "Search financial-need and funding-aware scholarship calls.",
            },
        ]

        expanded_templates: list[tuple[str, dict]] = []
        for template in templates:
            for country in target_countries:
                expanded_templates.append((country, template))
        return expanded_templates

    def _search_intent(self, normalized_profile: dict) -> dict:
        search_intent = normalized_profile.get("search_intent")
        if isinstance(search_intent, dict):
            return search_intent
        return normalized_profile

    def _format_query(
        self,
        template: str,
        values: dict[str, str],
        optional_values: dict[str, str],
    ) -> str:
        query = template
        for field, value in optional_values.items():
            placeholder = "{" + field + "?}"
            query = query.replace(placeholder, value or "")
        for field, value in values.items():
            placeholder = "{" + field + "}"
            query = query.replace(placeholder, value or "")
        query = self._compact_query(query)
        return query

    def _country_or_nationality_text(self, normalized_profile: dict) -> str:
        return (
            self._text(
                normalized_profile.get("country_or_nationality")
                or normalized_profile.get("country_of_origin")
                or normalized_profile.get("nationality")
            )
            or "international"
        )

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
        return field_of_study

    def _academic_level_text(self, normalized_profile: dict) -> str:
        academic_level = self._text(normalized_profile.get("academic_level"))
        if not academic_level or academic_level.casefold() in {
            "unspecified",
            "unknown",
            "not specified",
        }:
            return ""
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
                if country
                and country.casefold()
                not in {"any", "global", "unknown", "not specified"}
            ]
            if cleaned_countries:
                return cleaned_countries[:4]
        return ["global"]

    def _explicit_modality_text(self, normalized_profile: dict) -> str:
        modality = self._text(
            normalized_profile.get("modality")
            or normalized_profile.get("preferred_modality")
        )
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
