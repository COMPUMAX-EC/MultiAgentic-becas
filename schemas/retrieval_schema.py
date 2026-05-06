from __future__ import annotations


class RetrievalValidationError(ValueError):
    pass


def build_retrieval_result(
    scholarship_name: object,
    source_url: object,
    institution: object,
    country: object,
    academic_level: object,
    fields: object,
    benefits: object,
    deadline: object,
    application_status: object,
    retrieval_score: object,
    retrieval_reasons: object,
    source_reliability_score: object,
    **extra_fields: object,
) -> dict:
    cleaned_name = _clean_text(scholarship_name)
    if not cleaned_name:
        raise RetrievalValidationError("scholarship_name must be non-empty.")

    cleaned_source_url = _clean_text(source_url)
    if not cleaned_source_url:
        raise RetrievalValidationError("source_url must be non-empty.")

    result = {
        "scholarship_name": cleaned_name,
        "source_url": cleaned_source_url,
        "institution": _clean_text(institution),
        "country": _clean_text(country),
        "academic_level": _clean_text(academic_level),
        "fields": _clean_list(fields),
        "benefits": _clean_list(benefits),
        "deadline": _clean_text(deadline),
        "application_status": _clean_text(application_status) or "unknown",
        "retrieval_score": _clamp_score(retrieval_score),
        "retrieval_reasons": _clean_list(retrieval_reasons),
        "source_reliability_score": _clamp_score(source_reliability_score),
    }
    result.update(extra_fields)
    return result


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned_value = " ".join(value.strip().split())
    return cleaned_value or None


def _clean_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    cleaned_values: list[str] = []
    seen: set[str] = set()
    for item in value:
        cleaned_item = _clean_text(item)
        if not cleaned_item:
            continue
        comparison_key = cleaned_item.casefold()
        if comparison_key in seen:
            continue
        seen.add(comparison_key)
        cleaned_values.append(cleaned_item)
    return cleaned_values


def _clamp_score(value: object) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = 0
    return max(0, min(100, score))
