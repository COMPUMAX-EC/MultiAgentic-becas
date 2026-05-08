from __future__ import annotations

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


class ProfileAgent:
    def prepare_profile(self, raw_profile_data: dict) -> dict:
        validated_profile = validate_profile(raw_profile_data)

        normalized_profile = {
            "nationality": normalize_country(validated_profile["nationality"]),
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
