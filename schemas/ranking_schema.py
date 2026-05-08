from __future__ import annotations


ALLOWED_PRIORITY_LABELS = {
    "high_priority",
    "medium_priority",
    "possible_match",
    "low_priority",
    "insufficient_information",
    "not_recommended",
    "rejected",
}


class RankingValidationError(ValueError):
    pass


def build_ranking_result(
    rank: object,
    scholarship_name: object,
    source_url: object,
    final_score: object,
    compatibility_score: object,
    eligibility_decision: object,
    priority_label: object,
    ranking_reasons: object,
    risk_factors: object,
    missing_requirements: object,
    recommendation_summary: object,
    score_breakdown: object,
) -> dict:
    cleaned_rank = _positive_int(rank)
    if cleaned_rank is None:
        raise RankingValidationError("rank must be a positive integer.")

    cleaned_name = _clean_text(scholarship_name)
    if not cleaned_name:
        raise RankingValidationError("scholarship_name must be non-empty.")

    cleaned_source_url = _clean_text(source_url)
    if not cleaned_source_url:
        raise RankingValidationError("source_url must be non-empty.")

    cleaned_priority = _clean_text(priority_label)
    if cleaned_priority not in ALLOWED_PRIORITY_LABELS:
        raise RankingValidationError(f"Unsupported priority_label: {priority_label}")

    if not isinstance(score_breakdown, dict):
        raise RankingValidationError("score_breakdown must be a dictionary.")

    return {
        "rank": cleaned_rank,
        "scholarship_name": cleaned_name,
        "source_url": cleaned_source_url,
        "final_score": _clamp_score(final_score),
        "compatibility_score": _clamp_score(compatibility_score),
        "eligibility_decision": _clean_text(eligibility_decision) or "",
        "priority_label": cleaned_priority,
        "ranking_reasons": _clean_list(ranking_reasons),
        "risk_factors": _clean_list(risk_factors),
        "missing_requirements": _clean_list(missing_requirements),
        "recommendation_summary": _clean_text(recommendation_summary) or "",
        "score_breakdown": dict(score_breakdown),
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


def _positive_int(value: object) -> int | None:
    try:
        int_value = int(value)
    except (TypeError, ValueError):
        return None
    return int_value if int_value > 0 else None


def _clamp_score(value: object) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = 0
    return max(0, min(100, score))
