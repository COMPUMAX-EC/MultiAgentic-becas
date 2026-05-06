from __future__ import annotations


def normalize_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    cleaned_value = " ".join(value.strip().split())
    return cleaned_value or None


def normalize_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []

    normalized_values: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized_value = normalize_text(value)
        if normalized_value is None:
            continue

        comparison_key = normalized_value.casefold()
        if comparison_key in seen:
            continue

        seen.add(comparison_key)
        normalized_values.append(normalized_value)

    return normalized_values


def normalize_language_entries(languages: object) -> list[str]:
    normalized_languages: list[str] = []
    for language in normalize_list(languages):
        normalized_languages.append(" ".join(part.capitalize() for part in language.split()))
    return normalized_languages


def normalize_country(value: object) -> str | None:
    normalized_value = normalize_text(value)
    if normalized_value is None:
        return None
    return " ".join(part.capitalize() for part in normalized_value.split())


def normalize_academic_level(value: object) -> str | None:
    normalized_value = normalize_text(value)
    if normalized_value is None:
        return None

    academic_level_map = {
        "high school": "High School",
        "associate": "Associate",
        "bachelor": "Bachelor",
        "bachelors": "Bachelor",
        "master": "Master",
        "masters": "Master",
        "mba": "MBA",
        "phd": "PhD",
        "doctorate": "PhD",
        "postdoc": "Postdoc",
    }

    comparison_value = normalized_value.casefold()
    return academic_level_map.get(
        comparison_value,
        " ".join(part.capitalize() for part in normalized_value.split()),
    )
