from __future__ import annotations

from utils.url_utils import normalize_useful_url

ALLOWED_SOURCE_TYPES = {
    "university",
    "institute",
    "institution",
    "government",
    "organization",
    "foundation",
    "company",
    "international_organization",
    "official_pdf",
    "verified_news",
    "verified_newspaper",
    "verified_magazine",
    "verified_education_portal",
    "verified_scholarship_information_source",
    "scholarship_database",
    "unknown",
    "generic_blog",
    "irrelevant",
    "spam_or_low_quality",
    "expired_or_closed",
    # Backward-compatible values used by older cached records/tests.
    "official_university",
    "official_institute",
    "official_institution",
    "official_government",
    "official_organization",
    "official_foundation",
    "official_company",
    "official_announcement",
    "trusted_portal",
    "uncertain_source",
    "blog_or_media",
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

    validation_status = _acceptance_status(decision)
    warnings = _build_warnings(validation_status, source_type, risk_flags)
    validation_reason = _build_validation_reason(reasons, validation_status)

    url = normalize_useful_url(candidate_result.get("url"))
    source_url = normalize_useful_url(candidate_result.get("source_url")) or url
    original_url = normalize_useful_url(candidate_result.get("original_url")) or source_url

    return {
        "title": candidate_result.get("title", ""),
        "url": url,
        "source_url": source_url,
        "original_url": original_url,
        "snippet": candidate_result.get("snippet", ""),
        "source": candidate_result.get("source", ""),
        "source_domain": candidate_result.get("source_domain", ""),
        "query": candidate_result.get("query", ""),
        "query_used": candidate_result.get("query_used", candidate_result.get("query", "")),
        "target_country": candidate_result.get("target_country", ""),
        "source_type": source_type,
        "reliability_score": _clamp_score(reliability_score),
        "relevance_score": _clamp_score(relevance_score),
        "decision": decision,
        "acceptance_status": validation_status,
        "validation_status": validation_status,
        "validation_reason": validation_reason,
        "warnings": warnings,
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


def _build_validation_reason(reasons: list[str], validation_status: str) -> str:
    cleaned_reasons = [" ".join(str(reason).split()) for reason in reasons if str(reason).strip()]
    if cleaned_reasons:
        return cleaned_reasons[0]
    if validation_status == "accepted":
        return "Source appears official and relevant to scholarships."
    if validation_status == "accepted_with_warning":
        return "Source appears useful but needs extraction confirmation."
    return "Source did not pass validation."


def _build_warnings(
    validation_status: str,
    source_type: str,
    risk_flags: list[str],
) -> list[str]:
    warnings: list[str] = []
    if validation_status == "accepted_with_warning":
        if source_type.startswith("verified_"):
            warnings.append(
                "Source is verified informational source, not direct official application page."
            )
        else:
            warnings.append("Source may need extraction confirmation.")

    warning_by_flag = {
        "deadline_unknown": "Deadline could not be verified.",
        "official_link_not_extracted": "Official link has not yet been extracted.",
        "requirements_incomplete": "Requirements may be incomplete until extraction.",
        "source_type_inferred": "Source type was inferred and may need confirmation.",
        "informational_source": "Source is informational rather than a direct application page.",
    }
    for flag in risk_flags:
        warning = warning_by_flag.get(str(flag))
        if warning and warning not in warnings:
            warnings.append(warning)
    return warnings
