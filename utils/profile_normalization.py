from __future__ import annotations

import re
import unicodedata
from typing import Any


CEFR_LEVELS = ("a1", "a2", "b1", "b2", "c1", "c2")

COUNTRY_ALIASES = {
    "almania": "Germany",
    "alemania": "Germany",
    "germany": "Germany",
    "deutschland": "Germany",
    "allemagne": "Germany",
    "alemanha": "Germany",
    "canada": "Canada",
    "france": "France",
    "francia": "France",
    "franca": "France",
    "spain": "Spain",
    "espana": "Spain",
    "united states": "United States",
    "estados unidos": "United States",
    "usa": "United States",
    "us": "United States",
    "uk": "United Kingdom",
    "united kingdom": "United Kingdom",
    "reino unido": "United Kingdom",
    "netherlands": "Netherlands",
    "holanda": "Netherlands",
    "paises bajos": "Netherlands",
    "portugal": "Portugal",
    "brazil": "Brazil",
    "brasil": "Brazil",
    "colombia": "Colombia",
    "ecuador": "Ecuador",
    "mexico": "Mexico",
    "peru": "Peru",
    "argentina": "Argentina",
    "chile": "Chile",
}

NATIONALITY_ALIASES = {
    "colmbiano": ("Colombian", "Colombia"),
    "colmbiana": ("Colombian", "Colombia"),
    "colombiano": ("Colombian", "Colombia"),
    "colombiana": ("Colombian", "Colombia"),
    "colombian": ("Colombian", "Colombia"),
    "ecuatoriano": ("Ecuadorian", "Ecuador"),
    "ecuatoriana": ("Ecuadorian", "Ecuador"),
    "ecuadorian": ("Ecuadorian", "Ecuador"),
    "mexicano": ("Mexican", "Mexico"),
    "mexicana": ("Mexican", "Mexico"),
    "mexican": ("Mexican", "Mexico"),
    "peruano": ("Peruvian", "Peru"),
    "peruana": ("Peruvian", "Peru"),
    "peruvian": ("Peruvian", "Peru"),
    "argentino": ("Argentinian", "Argentina"),
    "argentina": ("Argentinian", "Argentina"),
    "argentinian": ("Argentinian", "Argentina"),
    "chileno": ("Chilean", "Chile"),
    "chilena": ("Chilean", "Chile"),
    "chilean": ("Chilean", "Chile"),
    "brasileno": ("Brazilian", "Brazil"),
    "brasilena": ("Brazilian", "Brazil"),
    "brazilian": ("Brazilian", "Brazil"),
}

ACADEMIC_LEVEL_ALIASES = {
    "pregrado": "undergraduate",
    "undergraduate": "undergraduate",
    "bachelor": "undergraduate",
    "bachelors": "undergraduate",
    "licenciatura": "undergraduate",
    "graduacao": "undergraduate",
    "master": "master",
    "masters": "master",
    "maestria": "master",
    "mestrado": "master",
    "mastere": "master",
    "msc": "master",
    "doctorado": "phd",
    "doutorado": "phd",
    "doctorat": "phd",
    "doctorate": "phd",
    "doctoral": "phd",
    "phd": "phd",
    "mba": "mba",
    "postdoc": "postdoc",
}

FIELD_ALIASES = {
    "ing sistemas": "Computer Science",
    "ingenieria de sistemas": "Computer Science",
    "ingenieria sistemas": "Computer Science",
    "systems engineering": "Computer Science",
    "computer science": "Computer Science",
    "ciencias de la computacion": "Computer Science",
    "informatica": "Computer Science",
    "software": "Software Engineering",
    "software engineering": "Software Engineering",
    "engenharia de software": "Software Engineering",
    "data science": "Data Science",
    "ciencia de datos": "Data Science",
    "ciencia dos dados": "Data Science",
    "cybersecurity": "Cybersecurity",
    "ciberseguridad": "Cybersecurity",
    "graphic design": "Graphic Design",
    "diseno grafico": "Graphic Design",
    "design grafico": "Graphic Design",
}

SPECIALIZATION_ALIASES = {
    "ia": "Artificial Intelligence",
    "ai": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "inteligencia artificial": "Artificial Intelligence",
    "intelligence artificielle": "Artificial Intelligence",
    "machine learning": "Machine Learning",
    "aprendizaje automatico": "Machine Learning",
}

SCHOLARSHIP_TYPE_ALIASES = {
    "beca completa": "Full funding",
    "financiacion completa": "Full funding",
    "fully funded": "Full funding",
    "full funding": "Full funding",
    "full scholarship": "Full funding",
    "beca parcial": "Partial funding",
    "financiacion parcial": "Partial funding",
    "partial funding": "Partial funding",
    "partial scholarship": "Partial funding",
    "parcial": "Partial funding",
}

LANGUAGE_ALIASES = {
    "ingles": "English",
    "english": "English",
    "inglish": "English",
    "espanol": "Spanish",
    "spanish": "Spanish",
    "castellano": "Spanish",
    "portugues": "Portuguese",
    "portuguese": "Portuguese",
    "frances": "French",
    "french": "French",
    "francais": "French",
    "aleman": "German",
    "german": "German",
    "deutsch": "German",
}

MODALITY_ALIASES = {
    "online": "Online",
    "virtual": "Online",
    "remoto": "Online",
    "remote": "Online",
    "hybrid": "Hybrid",
    "hibrido": "Hybrid",
    "hibrida": "Hybrid",
    "presencial": "On-campus",
    "on campus": "On-campus",
    "on-campus": "On-campus",
    "campus": "On-campus",
}


def infer_profile_from_text(raw_profile_text: str, scholarship_goal: str = "") -> dict:
    combined_text = " ".join(text for text in [raw_profile_text, scholarship_goal] if text)
    normalized_text = normalize_for_detection(combined_text)
    warnings: list[str] = []
    inferred_fields: list[str] = []

    detected_language = detect_input_language(normalized_text)
    nationality, origin_country = detect_nationality(normalized_text)
    target_countries = detect_target_countries(normalized_text, origin_country)
    academic_level = first_alias_match(normalized_text, ACADEMIC_LEVEL_ALIASES)
    field_of_study = first_alias_match(normalized_text, FIELD_ALIASES)
    specialization = first_alias_match(normalized_text, SPECIALIZATION_ALIASES)
    scholarship_type = first_alias_match(normalized_text, SCHOLARSHIP_TYPE_ALIASES)
    languages = infer_languages(normalized_text, detected_language)
    inferred_native_language = native_language_for_origin(origin_country, detected_language)
    if inferred_native_language and not has_language(languages, inferred_native_language):
        add_language(languages, inferred_native_language, "Native")
    preferred_modality = first_alias_match(normalized_text, MODALITY_ALIASES)

    if nationality:
        inferred_fields.append("nationality")
    else:
        nationality = "International"
        warnings.append("Country or nationality could not be confidently detected.")

    country_of_residence = detect_country_of_residence(normalized_text)
    if country_of_residence:
        inferred_fields.append("country_of_residence")
    elif origin_country:
        country_of_residence = origin_country
        warnings.append("Country of residence was inferred from nationality/origin.")
    else:
        country_of_residence = "Unknown"
        warnings.append("Country of residence is missing.")

    if origin_country:
        inferred_fields.append("country_of_origin")

    if target_countries:
        inferred_fields.append("target_countries")
    else:
        target_countries = ["Global"]
        warnings.append("Target countries are missing or not specific.")

    if academic_level:
        inferred_fields.append("academic_level")
    else:
        academic_level = "unspecified"
        warnings.append("Academic level is missing.")

    if specialization:
        inferred_fields.append("specialization")

    if field_of_study:
        inferred_fields.append("field_of_study")
    elif specialization:
        field_of_study = field_for_specialization(specialization)
        inferred_fields.append("field_of_study")
    else:
        field_of_study = "General studies"
        warnings.append("Field of study is ambiguous or missing.")

    interests = [field_of_study]
    if specialization and specialization not in interests:
        interests.append(specialization)

    if not languages:
        languages = [{"language": "Not specified", "level": None}]
        warnings.append("Languages are missing.")
    else:
        inferred_fields.append("languages")
        for language in languages:
            if language.get("level") is None:
                warnings.append(f"Language level is missing for {language['language']}.")

    if not scholarship_type:
        scholarship_type = "Unspecified funding"
        warnings.append("Scholarship type is unclear.")
    else:
        inferred_fields.append("scholarship_type")

    if not preferred_modality:
        preferred_modality = "Any"
        warnings.append("Modality is not specified.")
    else:
        inferred_fields.append("preferred_modality")

    warnings.append("Budget is missing.")

    return {
        "nationality": nationality,
        "country_of_origin": origin_country,
        "country_of_residence": country_of_residence,
        "languages": languages,
        "academic_level": academic_level,
        "field_of_study": field_of_study,
        "specialization": specialization,
        "interests": interests,
        "target_countries": target_countries,
        "scholarship_type": scholarship_type,
        "budget": {"currency": "usd", "max_personal_contribution": None},
        "preferred_modality": preferred_modality,
        "raw_profile_text": raw_profile_text,
        "original_input": combined_text,
        "detected_input_language": detected_language,
        "normalization_warnings": dedupe(warnings),
        "inferred_fields": sorted(set(inferred_fields)),
    }


def complete_profile_defaults(profile: dict) -> dict:
    completed_profile = dict(profile)
    warnings = list(completed_profile.get("normalization_warnings") or [])
    inferred_fields = set(completed_profile.get("inferred_fields") or [])

    def set_default(field: str, value: Any, warning: str) -> None:
        if completed_profile.get(field) not in (None, "", [], {}):
            return
        completed_profile[field] = value
        warnings.append(warning)

    set_default("nationality", "International", "Country or nationality is missing.")
    set_default(
        "country_of_residence",
        completed_profile.get("country_of_origin") or "Unknown",
        "Country of residence is missing.",
    )
    set_default(
        "languages",
        [{"language": "Not specified", "level": None}],
        "Languages are missing.",
    )
    set_default("academic_level", "unspecified", "Academic level is missing.")
    set_default("field_of_study", "General studies", "Field of study is ambiguous or missing.")
    set_default("target_countries", ["Global"], "Target countries are missing or not specific.")
    set_default("scholarship_type", "Unspecified funding", "Scholarship type is unclear.")
    set_default(
        "budget",
        {"currency": "usd", "max_personal_contribution": None},
        "Budget is missing.",
    )
    set_default("preferred_modality", "Any", "Modality is not specified.")

    if not completed_profile.get("interests"):
        completed_profile["interests"] = [completed_profile["field_of_study"]]
    if (
        completed_profile.get("specialization")
        and completed_profile["specialization"] not in completed_profile["interests"]
    ):
        completed_profile["interests"].append(completed_profile["specialization"])

    completed_profile["normalization_warnings"] = dedupe(warnings)
    completed_profile["inferred_fields"] = sorted(inferred_fields)
    return completed_profile


def normalize_for_detection(value: str) -> str:
    normalized_value = unicodedata.normalize("NFKD", str(value or "").casefold())
    without_accents = "".join(
        character
        for character in normalized_value
        if not unicodedata.combining(character)
    )
    without_punctuation = re.sub(r"[^a-z0-9+\s-]", " ", without_accents)
    return " ".join(without_punctuation.split())


def detect_input_language(normalized_text: str) -> str:
    signals = {
        "Spanish": ("soy", "quiero", "beca", "estudio", "maestria", "pregrado", "doctorado", "hablo"),
        "English": ("i am", "from", "scholarship", "study", "master", "bachelor", "speak"),
        "Portuguese": ("sou", "quero", "bolsa", "estudo", "mestrado", "doutorado", "falo"),
        "French": ("je suis", "bourse", "etudie", "mastere", "doctorat", "parle"),
    }
    counts = {
        language: sum(1 for signal in language_signals if phrase_in_text(normalized_text, signal))
        for language, language_signals in signals.items()
    }
    detected = [language for language, count in counts.items() if count > 0]
    if len(detected) > 1:
        return "Mixed"
    if detected:
        return detected[0]
    return "Unknown"


def detect_nationality(normalized_text: str) -> tuple[str | None, str | None]:
    for alias, (nationality, country) in NATIONALITY_ALIASES.items():
        if phrase_in_text(normalized_text, alias):
            return nationality, country

    origin_patterns = (
        r"\bfrom\s+([a-z ]{2,40})",
        r"\bde\s+([a-z ]{2,40})",
        r"\bdesde\s+([a-z ]{2,40})",
        r"\bsou\s+de\s+([a-z ]{2,40})",
    )
    for pattern in origin_patterns:
        match = re.search(pattern, normalized_text)
        if match:
            country = country_from_fragment(match.group(1))
            if country:
                return nationality_for_country(country), country
    return None, None


def detect_country_of_residence(normalized_text: str) -> str | None:
    patterns = (
        r"\blive in\s+([a-z ]{2,40})",
        r"\bliving in\s+([a-z ]{2,40})",
        r"\bvivo en\s+([a-z ]{2,40})",
        r"\bresido en\s+([a-z ]{2,40})",
        r"\bmoro em\s+([a-z ]{2,40})",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if match:
            country = country_from_fragment(match.group(1))
            if country:
                return country
    return None


def detect_target_countries(normalized_text: str, origin_country: str | None) -> list[str]:
    countries = values_from_aliases(normalized_text, COUNTRY_ALIASES)
    if origin_country:
        countries = [country for country in countries if country != origin_country]
    return countries


def infer_languages(normalized_text: str, detected_language: str) -> list[dict]:
    languages: list[dict] = []
    for alias, language in LANGUAGE_ALIASES.items():
        if not phrase_in_text(normalized_text, alias):
            continue
        add_language(languages, language, detect_language_level(normalized_text, alias))
    return languages


def detect_language_level(normalized_text: str, language_alias: str) -> str | None:
    alias_pattern = re.escape(language_alias)
    after_pattern = rf"\b{alias_pattern}\b(?:\s+(?:e|and|y|et))?\s+({'|'.join(CEFR_LEVELS)}|native|nativo|nativa)\b"
    after_match = re.search(after_pattern, normalized_text)
    if after_match:
        return normalize_language_level(after_match.group(1))

    before_pattern = rf"\b({'|'.join(CEFR_LEVELS)}|native|nativo|nativa)\s+{alias_pattern}\b"
    before_match = re.search(before_pattern, normalized_text)
    if before_match:
        return normalize_language_level(before_match.group(1))
    return None


def normalize_language_level(value: str) -> str:
    normalized_value = normalize_for_detection(value)
    if normalized_value in {"native", "nativo", "nativa"}:
        return "Native"
    return normalized_value.upper()


def first_alias_match(normalized_text: str, aliases: dict[str, str]) -> str | None:
    for alias, value in sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True):
        if phrase_in_text(normalized_text, alias):
            return value
    return None


def values_from_aliases(normalized_text: str, aliases: dict[str, str]) -> list[str]:
    values: list[str] = []
    for alias, value in sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True):
        if phrase_in_text(normalized_text, alias) and value not in values:
            values.append(value)
    return values


def country_from_fragment(fragment: str) -> str | None:
    normalized_fragment = normalize_for_detection(fragment)
    for alias, country in sorted(COUNTRY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if normalized_fragment.startswith(alias) or phrase_in_text(normalized_fragment, alias):
            return country
    return None


def nationality_for_country(country: str) -> str:
    nationalities = {
        "Colombia": "Colombian",
        "Ecuador": "Ecuadorian",
        "Mexico": "Mexican",
        "Peru": "Peruvian",
        "Argentina": "Argentinian",
        "Chile": "Chilean",
        "Brazil": "Brazilian",
    }
    return nationalities.get(country, f"{country} applicant")


def field_for_specialization(specialization: str) -> str:
    if specialization in {"Artificial Intelligence", "Machine Learning"}:
        return "Computer Science"
    return "General studies"


def native_language_for_origin(
    origin_country: str | None,
    detected_language: str,
) -> str | None:
    if detected_language not in {"Spanish", "Mixed"}:
        return None
    spanish_speaking_countries = {
        "Argentina",
        "Chile",
        "Colombia",
        "Ecuador",
        "Mexico",
        "Peru",
        "Spain",
    }
    if origin_country in spanish_speaking_countries:
        return "Spanish"
    return None


def add_language(languages: list[dict], language: str, level: str | None) -> None:
    for existing_language in languages:
        if existing_language["language"] != language:
            continue
        if existing_language.get("level") is None and level is not None:
            existing_language["level"] = level
        return
    languages.append({"language": language, "level": level})


def has_language(languages: list[dict], language: str) -> bool:
    return any(entry.get("language") == language for entry in languages)


def phrase_in_text(normalized_text: str, phrase: str) -> bool:
    normalized_phrase = normalize_for_detection(phrase)
    return re.search(rf"(?<![a-z0-9]){re.escape(normalized_phrase)}(?![a-z0-9])", normalized_text) is not None


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        cleaned = " ".join(str(value).split())
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return deduped
