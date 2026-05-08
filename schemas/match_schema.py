from __future__ import annotations


ALLOWED_ELIGIBILITY_DECISIONS = {
    "confirmed_match",
    "likely_match",
    "possible_match",
    "insufficient_information",
    "mismatch",
    "rejected",
    # Backward-compatible labels from the earlier matcher.
    "strong_match",
    "weak_match",
    "not_eligible",
}

BREAKDOWN_FIELDS = (
    "nationality_score",
    "academic_level_score",
    "field_score",
    "target_country_score",
    "language_score",
    "funding_score",
    "scholarship_type_score",
    "modality_score",
    "source_reliability_score",
    "deadline_status_score",
    "link_score",
)


class MatchValidationError(ValueError):
    pass


def build_match_result(
    scholarship_name: object,
    source_url: object,
    compatibility_score: object,
    eligibility_decision: object,
    matched_factors: object,
    missing_requirements: object,
    risk_factors: object,
    score_breakdown: object,
    recommendation_reason: object,
) -> dict:
    cleaned_name = _clean_text(scholarship_name)
    if not cleaned_name:
        raise MatchValidationError("scholarship_name must be non-empty.")

    cleaned_source_url = _clean_text(source_url)
    if not cleaned_source_url:
        raise MatchValidationError("source_url must be non-empty.")

    cleaned_decision = _clean_text(eligibility_decision)
    if cleaned_decision not in ALLOWED_ELIGIBILITY_DECISIONS:
        raise MatchValidationError(
            f"Unsupported eligibility_decision: {eligibility_decision}"
        )

    if not isinstance(score_breakdown, dict):
        raise MatchValidationError("score_breakdown must be a dictionary.")

    cleaned_breakdown = {
        field: _clamp_score(score_breakdown.get(field, 0)) for field in BREAKDOWN_FIELDS
    }

    return {
        "scholarship_name": cleaned_name,
        "source_url": cleaned_source_url,
        "compatibility_score": _clamp_score(compatibility_score),
        "eligibility_decision": cleaned_decision,
        "matched_factors": _clean_list(matched_factors),
        "missing_requirements": _clean_list(missing_requirements),
        "risk_factors": _clean_list(risk_factors),
        "score_breakdown": cleaned_breakdown,
        "recommendation_reason": _clean_text(recommendation_reason) or "",
    }


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
