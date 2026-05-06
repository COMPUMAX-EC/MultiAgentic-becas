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


def normalize_language_profiles(languages: object) -> list[dict]:
    if not isinstance(languages, list):
        return []

    normalized_languages: list[dict] = []
    seen: set[tuple[str, str | None]] = set()

    for entry in languages:
        normalized_entry = _normalize_language_entry(entry)
        if normalized_entry is None:
            continue

        comparison_key = (
            normalized_entry["language"].casefold(),
            normalized_entry["level"].casefold()
            if isinstance(normalized_entry["level"], str)
            else None,
        )
        if comparison_key in seen:
            continue

        seen.add(comparison_key)
        normalized_languages.append(normalized_entry)

    return normalized_languages


def normalize_language_entries(languages: object) -> list[str]:
    return [entry["display"] for entry in normalize_language_profiles(languages)]


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


def _normalize_language_entry(value: object) -> dict | None:
    if isinstance(value, str):
        language_text = normalize_text(value)
        if language_text is None:
            return None
        language_name, language_level = _split_language_and_level(language_text)
        return _build_language_profile(language_name, language_level)

    if isinstance(value, dict):
        language_name = _normalize_language_name(value.get("language"))
        if language_name is None:
            return None
        language_level = _normalize_language_level(value.get("level"))
        return _build_language_profile(language_name, language_level)

    return None


def _build_language_profile(language_name: str, language_level: str | None) -> dict:
    display = language_name if language_level is None else f"{language_name} {language_level}"
    return {
        "language": language_name,
        "level": language_level,
        "display": display,
    }


def _split_language_and_level(language_text: str) -> tuple[str, str | None]:
    parts = language_text.split()
    if len(parts) >= 2 and _looks_like_language_level(parts[-1]):
        language_name = _normalize_language_name(" ".join(parts[:-1]))
        language_level = _normalize_language_level(parts[-1])
        if language_name is not None:
            return language_name, language_level
    language_name = _normalize_language_name(language_text)
    return language_name or language_text, None


def _normalize_language_name(value: object) -> str | None:
    normalized_value = normalize_text(value)
    if normalized_value is None:
        return None
    return " ".join(part.capitalize() for part in normalized_value.split())


def _normalize_language_level(value: object) -> str | None:
    normalized_value = normalize_text(value)
    if normalized_value is None:
        return None
    if normalized_value.casefold() == "native":
        return "Native"
    return normalized_value.upper() if _looks_like_language_level(normalized_value) else normalized_value


def _looks_like_language_level(value: str) -> bool:
    comparison_value = value.casefold()
    known_levels = {
        "native",
        "a1",
        "a2",
        "b1",
        "b2",
        "c1",
        "c2",
    }
    return comparison_value in known_levels
