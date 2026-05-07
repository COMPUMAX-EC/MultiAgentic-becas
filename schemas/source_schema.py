from __future__ import annotations


ALLOWED_SOURCE_TYPES = {
    "official_university",
    "official_institute",
    "official_institution",
    "official_government",
    "official_organization",
    "official_foundation",
    "official_company",
    "official_pdf",
    "official_announcement",
    "verified_news",
    "trusted_portal",
    "scholarship_database",
    "uncertain_source",
    "blog_or_media",
    "irrelevant",
    "spam_or_low_quality",
    "expired_or_closed",
}

ALLOWED_DECISIONS = {"accept", "review", "reject"}


class SourceValidationError(ValueError):
    pass


def build_validated_source(
    candidate_result: dict,
    source_type: str,
    reliability_score: int,
    relevance_score: int,
    decision: str,
    reasons: list[str],
    risk_flags: list[str],
) -> dict:
    if source_type not in ALLOWED_SOURCE_TYPES:
        raise SourceValidationError(f"Unsupported source_type: {source_type}")
    if decision not in ALLOWED_DECISIONS:
        raise SourceValidationError(f"Unsupported decision: {decision}")

    return {
        "title": candidate_result.get("title", ""),
        "url": candidate_result.get("url", ""),
        "snippet": candidate_result.get("snippet", ""),
        "query": candidate_result.get("query", ""),
        "target_country": candidate_result.get("target_country", ""),
        "source_type": source_type,
        "reliability_score": _clamp_score(reliability_score),
        "relevance_score": _clamp_score(relevance_score),
        "decision": decision,
        "acceptance_status": _acceptance_status(decision),
        "reasons": reasons,
        "risk_flags": risk_flags,
    }


def _clamp_score(score: int) -> int:
    return max(0, min(100, int(score)))


def _acceptance_status(decision: str) -> str:
    if decision == "accept":
        return "accepted"
    if decision == "review":
        return "accepted_with_warning"
    return "rejected"
