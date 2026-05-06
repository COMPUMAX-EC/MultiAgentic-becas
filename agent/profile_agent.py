from __future__ import annotations

from schemas.profile_schema import validate_profile
from utils.normalizer import (
    normalize_academic_level,
    normalize_country,
    normalize_language_entries,
    normalize_list,
    normalize_text,
)


class ProfileAgent:
    def prepare_profile(self, raw_profile_data: dict) -> dict:
        validated_profile = validate_profile(raw_profile_data)

        normalized_profile = {
            "nationality": normalize_country(validated_profile["nationality"]),
            "country_of_residence": normalize_country(
                validated_profile["country_of_residence"]
            ),
            "languages": normalize_language_entries(validated_profile["languages"]),
            "academic_level": normalize_academic_level(
                validated_profile["academic_level"]
            ),
            "field_of_study": normalize_text(validated_profile["field_of_study"]),
            "interests": normalize_list(validated_profile["interests"]),
            "target_countries": normalize_list(
                [
                    normalize_country(country)
                    for country in validated_profile["target_countries"]
                ]
            ),
            "scholarship_type": normalize_text(validated_profile["scholarship_type"]),
            "budget": self._normalize_budget(validated_profile["budget"]),
            "preferred_modality": normalize_text(
                validated_profile["preferred_modality"]
            ),
        }

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
