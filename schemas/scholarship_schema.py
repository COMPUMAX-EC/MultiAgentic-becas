from __future__ import annotations


ALLOWED_APPLICATION_STATUSES = {"open", "closed", "unknown", "upcoming"}
LIST_FIELDS = (
    "eligible_nationalities",
    "required_languages",
    "fields",
    "benefits",
    "requirements",
    "evidence_snippets",
)


class ScholarshipValidationError(ValueError):
    pass


def validate_scholarship_extractions(
    raw_scholarships: object,
    source_metadata: dict,
    min_confidence: int = 0,
) -> list[dict]:
    if not isinstance(raw_scholarships, list):
        raise ScholarshipValidationError("Scholarship extraction must be a list.")

    cleaned_scholarships: list[dict] = []
    for raw_scholarship in raw_scholarships:
        if not isinstance(raw_scholarship, dict):
            continue

        scholarship_name = _clean_text(raw_scholarship.get("scholarship_name"))
        if not scholarship_name:
            continue

        extraction_confidence = _clean_confidence(
            raw_scholarship.get("extraction_confidence")
        )
        if extraction_confidence < min_confidence:
            continue

        application_status = _clean_application_status(
            raw_scholarship.get("application_status")
        )
        source_url = _clean_text(source_metadata.get("source_url"))
        if not source_url:
            raise ScholarshipValidationError("source_url must be preserved.")
        official_link = _clean_text(raw_scholarship.get("official_link"))
        application_url = _clean_text(raw_scholarship.get("application_url"))
        pdf_url = _clean_text(raw_scholarship.get("pdf_url")) or _clean_text(
            source_metadata.get("pdf_url")
        )
        display_link = _first_text(official_link, application_url, source_url, pdf_url)

        cleaned_scholarship = {
            "scholarship_name": scholarship_name,
            "institution": _clean_text(raw_scholarship.get("institution")),
            "country": _clean_text(raw_scholarship.get("country")),
            "academic_level": _clean_text(raw_scholarship.get("academic_level")),
            "eligible_nationalities": _clean_list(
                raw_scholarship.get("eligible_nationalities")
            ),
            "required_languages": _clean_list(
                raw_scholarship.get("required_languages")
            ),
            "fields": _clean_list(raw_scholarship.get("fields")),
            "benefits": _clean_list(raw_scholarship.get("benefits")),
            "deadline": _clean_text(raw_scholarship.get("deadline")),
            "requirements": _clean_list(raw_scholarship.get("requirements")),
            "application_status": application_status,
            "source_url": source_url,
            "official_link": official_link,
            "application_url": application_url,
            "pdf_url": pdf_url,
            "display_link": display_link,
            "source_type": _clean_text(source_metadata.get("source_type")),
            "source_reliability_score": _clean_score(
                source_metadata.get("source_reliability_score")
            ),
            "extraction_confidence": extraction_confidence,
            "evidence_snippets": _clean_list(
                raw_scholarship.get("evidence_snippets")
            ),
        }
        cleaned_scholarships.append(cleaned_scholarship)

    if not cleaned_scholarships:
        raise ScholarshipValidationError("No valid scholarships were extracted.")

    return cleaned_scholarships


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned_value = " ".join(value.strip().split())
    return cleaned_value or None


def _clean_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    cleaned_values: list[str] = []
    for item in value:
        cleaned_item = _clean_text(item)
        if cleaned_item:
            cleaned_values.append(cleaned_item)
    return cleaned_values


def _clean_confidence(value: object) -> int:
    return _clean_score(value)


def _clean_score(value: object) -> int:
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 0


def _clean_application_status(value: object) -> str:
    if not isinstance(value, str):
        return "unknown"

    normalized_value = value.strip().lower()
    if normalized_value not in ALLOWED_APPLICATION_STATUSES:
        return "unknown"
    return normalized_value


def _first_text(*values: str | None) -> str:
    for value in values:
        if value:
            return value
    return ""
