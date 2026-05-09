from __future__ import annotations

import hashlib
import json
from typing import Any

from schemas.profile_schema import validate_profile
from utils.normalizer import (
    normalize_academic_level,
    normalize_country,
    normalize_language_profiles,
    normalize_list,
    normalize_text,
)
from utils.profile_normalization import (
    FIELD_ALIASES,
    MODALITY_ALIASES,
    SCHOLARSHIP_TYPE_ALIASES,
    SPECIALIZATION_ALIASES,
    first_alias_match,
    normalize_for_detection,
)


MINIMUM_REQUIRED_FIELDS = (
    "country_or_nationality",
    "languages",
    "scholarship_type",
)

MISSING_COUNTRY_VALUES = {
    "",
    "international",
    "unknown",
    "not specified",
    "unspecified",
}

MISSING_LANGUAGE_VALUES = {
    "",
    "not specified",
    "unknown",
    "unspecified",
}

MISSING_SCHOLARSHIP_TYPE_VALUES = {
    "",
    "scholarship",
    "funding",
    "unspecified",
    "unspecified funding",
    "unknown",
    "not specified",
}

MISSING_OPTIONAL_VALUES = {
    "",
    "any",
    "global",
    "general studies",
    "no preference",
    "not specified",
    "unknown",
    "unspecified",
}

EXPLICIT_MODALITY_VALUES = {"online", "on-campus", "hybrid"}


class ProfileAgent:
    def prepare_profile(self, raw_profile_data: dict) -> dict:
        validated_profile = validate_profile(raw_profile_data)

        country_of_origin = raw_profile_data.get("country_of_origin")
        normalized_origin = normalize_country(country_of_origin)
        normalized_nationality = normalize_country(validated_profile["nationality"])

        normalized_profile = {
            "nationality": normalized_nationality,
            "country_or_nationality": normalized_origin or normalized_nationality,
            "country_of_residence": normalize_country(
                validated_profile["country_of_residence"]
            ),
            "languages": normalize_language_profiles(validated_profile["languages"]),
            "academic_level": normalize_academic_level(
                validated_profile["academic_level"]
            ),
            "field_of_study": self._normalize_alias_text(
                validated_profile["field_of_study"],
                FIELD_ALIASES,
            ),
            "interests": normalize_list(validated_profile["interests"]),
            "target_countries": normalize_list(
                [
                    normalize_country(country)
                    for country in validated_profile["target_countries"]
                ]
            ),
            "scholarship_type": self._normalize_alias_text(
                validated_profile["scholarship_type"],
                SCHOLARSHIP_TYPE_ALIASES,
            ),
            "budget": self._normalize_budget(validated_profile["budget"]),
            "preferred_modality": self._normalize_alias_text(
                validated_profile["preferred_modality"],
                MODALITY_ALIASES,
            ),
        }
        self._copy_optional_profile_metadata(raw_profile_data, normalized_profile)

        return normalized_profile

    def validate_minimum_required_input(self, normalized_profile: dict) -> dict:
        missing_required_fields = []

        if not self._has_country_or_nationality(normalized_profile):
            missing_required_fields.append("country_or_nationality")
        if not self._has_languages(normalized_profile):
            missing_required_fields.append("languages")
        if not self._has_scholarship_type(normalized_profile):
            missing_required_fields.append("scholarship_type")

        if missing_required_fields:
            return {
                "status": "needs_more_information",
                "missing_required_fields": missing_required_fields,
                "message": (
                    "To start the scholarship search, please provide your country "
                    "or nationality, language(s), and scholarship type."
                ),
            }

        return {
            "status": "ready",
            "missing_required_fields": [],
            "message": "Minimum required scholarship search information is present.",
        }

    def build_search_intent(self, normalized_profile: dict) -> dict:
        warnings = list(normalized_profile.get("normalization_warnings") or [])
        search_intent: dict[str, Any] = {
            "missing_optional_fields": self._missing_optional_fields(normalized_profile),
            "warnings": warnings,
        }

        country_or_nationality = self._country_or_nationality(normalized_profile)
        if country_or_nationality:
            search_intent["country_or_nationality"] = country_or_nationality

        languages = self._searchable_languages(normalized_profile.get("languages"))
        if languages:
            search_intent["languages"] = languages

        scholarship_type = self._searchable_scholarship_type(normalized_profile)
        if scholarship_type:
            search_intent["scholarship_type"] = scholarship_type

        for field in ("academic_level", "field_of_study", "specialization"):
            value = self._searchable_text(normalized_profile.get(field))
            if value:
                search_intent[field] = value

        target_countries = self._searchable_list(normalized_profile.get("target_countries"))
        if target_countries:
            search_intent["target_countries"] = target_countries

        budget = self._searchable_budget(normalized_profile.get("budget"))
        if budget:
            search_intent["budget"] = budget

        modality = self._explicit_modality(normalized_profile)
        if modality:
            search_intent["modality"] = modality

        search_intent["search_specificity"] = self._search_specificity(search_intent)
        search_intent["search_signature"] = self.build_search_signature(search_intent)
        return search_intent

    def build_search_signature(self, search_intent: dict) -> dict:
        signature_payload: dict[str, Any] = {}
        for field in ("country_or_nationality", "languages", "scholarship_type", "budget"):
            if field in search_intent:
                signature_payload[field] = search_intent[field]
        if self._is_explicit_modality(search_intent.get("modality")):
            signature_payload["modality"] = search_intent["modality"]

        signature_json = json.dumps(
            signature_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return {
            "key": hashlib.sha256(signature_json.encode("utf-8")).hexdigest(),
            "payload": signature_payload,
        }

    def _normalize_budget(self, budget: int | float | dict) -> int | float | dict:
        if isinstance(budget, dict):
            normalized_budget = {}
            for key, value in budget.items():
                normalized_key = normalize_text(str(key)).lower().replace(" ", "_")
                if isinstance(value, str):
                    cleaned_value = normalize_text(value)
                    if cleaned_value is not None:
                        normalized_budget[normalized_key] = cleaned_value
                else:
                    normalized_budget[normalized_key] = value
            return normalized_budget

        return budget

    def _normalize_alias_text(self, value: object, aliases: dict[str, str]) -> str | None:
        normalized_value = normalize_text(value)
        if normalized_value is None:
            return None

        alias_value = first_alias_match(normalize_for_detection(normalized_value), aliases)
        return alias_value or normalized_value

    def _copy_optional_profile_metadata(
        self,
        raw_profile_data: dict,
        normalized_profile: dict,
    ) -> None:
        metadata_fields = (
            "raw_profile_text",
            "original_input",
            "detected_input_language",
            "normalization_warnings",
            "inferred_fields",
            "country_of_origin",
            "specialization",
        )
        for field in metadata_fields:
            if field not in raw_profile_data:
                continue
            value = raw_profile_data[field]
            if field == "country_of_origin":
                normalized_profile[field] = normalize_country(value)
            elif field == "specialization":
                normalized_profile[field] = self._normalize_alias_text(
                    value,
                    SPECIALIZATION_ALIASES,
                )
            else:
                normalized_profile[field] = value

        if normalized_profile.get("country_of_origin"):
            normalized_profile["country_or_nationality"] = normalized_profile[
                "country_of_origin"
            ]

    def _has_country_or_nationality(self, normalized_profile: dict) -> bool:
        return bool(self._country_or_nationality(normalized_profile))

    def _has_languages(self, normalized_profile: dict) -> bool:
        return bool(self._searchable_languages(normalized_profile.get("languages")))

    def _has_scholarship_type(self, normalized_profile: dict) -> bool:
        return bool(self._searchable_scholarship_type(normalized_profile))

    def _country_or_nationality(self, normalized_profile: dict) -> str | None:
        for field in ("country_or_nationality", "country_of_origin", "nationality"):
            value = self._searchable_text(
                normalized_profile.get(field),
                missing_values=MISSING_COUNTRY_VALUES,
            )
            if value:
                return value
        return None

    def _searchable_scholarship_type(self, normalized_profile: dict) -> str | None:
        return self._searchable_text(
            normalized_profile.get("scholarship_type"),
            missing_values=MISSING_SCHOLARSHIP_TYPE_VALUES,
        )

    def _searchable_languages(self, value: object) -> list[dict]:
        languages = normalize_language_profiles(value)
        searchable_languages = []
        for language in languages:
            language_name = self._searchable_text(
                language.get("language"),
                missing_values=MISSING_LANGUAGE_VALUES,
            )
            if not language_name:
                continue
            searchable_languages.append(language)
        return searchable_languages

    def _missing_optional_fields(self, normalized_profile: dict) -> list[str]:
        missing_fields = []
        if not self._searchable_text(normalized_profile.get("academic_level")):
            missing_fields.append("academic_level")
        if not self._searchable_text(normalized_profile.get("field_of_study")):
            missing_fields.append("field_of_study")
        if not self._searchable_text(normalized_profile.get("specialization")):
            missing_fields.append("specialization")
        if not self._searchable_list(normalized_profile.get("target_countries")):
            missing_fields.append("target_countries")
        if not self._searchable_budget(normalized_profile.get("budget")):
            missing_fields.append("budget")
        if not self._explicit_modality(normalized_profile):
            missing_fields.append("modality")
        return missing_fields

    def _searchable_list(self, value: object) -> list[str]:
        return [
            item
            for item in normalize_list(value)
            if item.casefold() not in MISSING_OPTIONAL_VALUES
        ]

    def _searchable_budget(self, value: object) -> dict | int | float | None:
        if isinstance(value, dict):
            contribution = value.get("max_personal_contribution")
            has_contribution = contribution not in (None, "")
            if not has_contribution:
                return None
            return self._normalize_budget(value)
        if isinstance(value, (int, float)):
            return value
        return None

    def _explicit_modality(self, normalized_profile: dict) -> str | None:
        modality = self._searchable_text(normalized_profile.get("preferred_modality"))
        if self._is_explicit_modality(modality):
            return modality
        return None

    def _is_explicit_modality(self, value: object) -> bool:
        normalized_value = normalize_text(value)
        if normalized_value is None:
            return False
        return normalized_value.casefold() in EXPLICIT_MODALITY_VALUES

    def _searchable_text(
        self,
        value: object,
        missing_values: set[str] = MISSING_OPTIONAL_VALUES,
    ) -> str | None:
        normalized_value = normalize_text(value)
        if normalized_value is None:
            return None
        if normalized_value.casefold() in missing_values:
            return None
        return normalized_value

    def _search_specificity(self, search_intent: dict) -> str:
        has_academic_level = "academic_level" in search_intent
        has_field_or_specialization = (
            "field_of_study" in search_intent or "specialization" in search_intent
        )
        has_target_country = bool(search_intent.get("target_countries"))

        if has_academic_level and has_field_or_specialization and has_target_country:
            return "specific"
        if has_academic_level or has_field_or_specialization or has_target_country:
            return "moderate"
        return "general"
