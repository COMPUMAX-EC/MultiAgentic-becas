from __future__ import annotations

from tools.date_validator import detect_status_from_deadline, has_obvious_expired_signal
from utils.url_utils import first_useful_url, normalize_useful_url

ALLOWED_APPLICATION_STATUSES = {"open", "closed", "unknown", "upcoming"}
ALLOWED_DEADLINE_STATUSES = {"open", "closed", "unknown", "upcoming"}
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
        source_url = first_useful_url(
            source_metadata.get("source_url"),
            source_metadata.get("original_url"),
            source_metadata.get("url"),
            raw_scholarship.get("source_url"),
        )
        if not source_url:
            raise ScholarshipValidationError("source_url must be preserved.")
        official_link = first_useful_url(
            raw_scholarship.get("official_link"),
            raw_scholarship.get("official_url"),
        )
        application_url = first_useful_url(
            raw_scholarship.get("application_url"),
            raw_scholarship.get("apply_url"),
        )
        pdf_url = normalize_useful_url(raw_scholarship.get("pdf_url")) or normalize_useful_url(
            source_metadata.get("pdf_url")
        )
        display_link = resolve_display_link(
            {
                "official_link": official_link,
                "application_url": application_url,
                "source_url": source_url,
                "pdf_url": pdf_url,
            }
        )
        if not display_link:
            continue

        deadline = _clean_text(raw_scholarship.get("deadline"))
        deadline_status = _clean_deadline_status(
            raw_scholarship.get("deadline_status"),
            deadline,
            raw_scholarship,
        )

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
            "deadline": deadline,
            "deadline_status": deadline_status,
            "requirements": _clean_list(raw_scholarship.get("requirements")),
            "application_status": application_status,
            "source_url": source_url,
            "official_link": official_link,
            "application_url": application_url,
            "pdf_url": pdf_url,
            "display_link": display_link,
            "original_url": source_metadata.get("original_url"),
            "query_used": source_metadata.get("query_used"),
            "query_family": source_metadata.get("query_family"),
            "source_family": source_metadata.get("source_family"),
            "source_type": _clean_text(source_metadata.get("source_type")),
            "source_validation_status": source_metadata.get("source_validation_status"),
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


def resolve_link_fields(record: dict) -> dict:
    official_link = first_useful_url(
        record.get("official_link"),
        record.get("official_url"),
    )
    application_url = first_useful_url(
        record.get("application_url"),
        record.get("apply_url"),
    )
    source_url = first_useful_url(
        record.get("source_url"),
        record.get("url"),
        record.get("link"),
    )
    pdf_url = first_useful_url(record.get("pdf_url"))
    return {
        "official_link": official_link,
        "application_url": application_url,
        "source_url": source_url,
        "pdf_url": pdf_url,
        "display_link": first_useful_url(official_link, application_url, source_url, pdf_url),
    }


def resolve_display_link(record: dict) -> str:
    return resolve_link_fields(record)["display_link"]


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


def _clean_deadline_status(
    value: object,
    deadline: str | None,
    raw_scholarship: dict,
) -> str:
    if isinstance(value, str):
        normalized_value = value.strip().lower()
        if normalized_value in ALLOWED_DEADLINE_STATUSES:
            return normalized_value

    if not deadline:
        application_status = str(raw_scholarship.get("application_status") or "").lower()
        return "closed" if application_status == "closed" else "unknown"

    text = " ".join(
        str(item or "")
        for item in (
            deadline,
            raw_scholarship.get("scholarship_name"),
            raw_scholarship.get("application_status"),
            " ".join(_clean_list(raw_scholarship.get("evidence_snippets"))),
        )
    )
    if has_obvious_expired_signal(text, ""):
        return "closed"
    detected_status = detect_status_from_deadline(
        deadline,
        raw_scholarship.get("application_status"),
    )
    if detected_status == "expired":
        return "closed"
    if detected_status in ALLOWED_DEADLINE_STATUSES:
        return detected_status
    return "unknown"


def _first_text(*values: str | None) -> str:
    for value in values:
        if value:
            return value
    return ""
