from __future__ import annotations

import difflib


def build_text_for_scholarship(scholarship: dict) -> str:
    parts = [
        scholarship.get("scholarship_name"),
        scholarship.get("institution"),
        scholarship.get("country"),
        scholarship.get("academic_level"),
        " ".join(scholarship.get("fields", [])),
        " ".join(scholarship.get("benefits", [])),
        " ".join(scholarship.get("eligible_nationalities", [])),
        " ".join(scholarship.get("required_languages", [])),
        " ".join(scholarship.get("requirements", [])),
    ]
    return " ".join(str(part).strip() for part in parts if part).strip()


def simple_text_similarity(profile_text: str, scholarship_text: str) -> int:
    if not profile_text or not scholarship_text:
        return 0
    ratio = difflib.SequenceMatcher(
        None,
        profile_text.casefold(),
        scholarship_text.casefold(),
    ).ratio()
    return max(0, min(100, int(round(ratio * 100))))
