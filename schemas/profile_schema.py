from __future__ import annotations


REQUIRED_PROFILE_FIELDS = (
    "nationality",
    "country_of_residence",
    "languages",
    "academic_level",
    "field_of_study",
    "interests",
    "target_countries",
    "scholarship_type",
    "budget",
    "preferred_modality",
)

LIST_FIELDS = ("languages", "interests", "target_countries")


class ProfileValidationError(ValueError):
    pass


def validate_profile(profile_data: dict) -> dict:
    if not isinstance(profile_data, dict):
        raise ProfileValidationError("Profile content must be a JSON object.")

    missing_fields = [
        field
        for field in REQUIRED_PROFILE_FIELDS
        if field not in profile_data or profile_data[field] is None
    ]
    if missing_fields:
        raise ProfileValidationError(
            f"Missing required profile fields: {', '.join(missing_fields)}"
        )

    validated_profile = {}
    for field in REQUIRED_PROFILE_FIELDS:
        value = profile_data[field]
        if field in LIST_FIELDS:
            if not isinstance(value, list):
                raise ProfileValidationError(
                    f"Field '{field}' must be a list."
                )
            if not value:
                raise ProfileValidationError(
                    f"Field '{field}' must be a non-empty list."
                )
            if not any(isinstance(item, str) and item.strip() for item in value):
                raise ProfileValidationError(
                    f"Field '{field}' must contain at least one non-empty text value."
                )
            validated_profile[field] = value
            continue

        if isinstance(value, str):
            if not value.strip():
                raise ProfileValidationError(f"Field '{field}' cannot be empty.")
            validated_profile[field] = value
            continue

        if field == "budget" and isinstance(value, (int, float)):
            validated_profile[field] = value
            continue

        if field == "budget" and isinstance(value, dict) and value:
            validated_profile[field] = value
            continue

        raise ProfileValidationError(
            f"Field '{field}' has an invalid type: {type(value).__name__}."
        )

    return validated_profile
