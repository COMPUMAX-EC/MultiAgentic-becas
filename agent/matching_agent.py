from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from config.settings import settings
from llm.provider import LLMProviderError, generate_text
from schemas.match_schema import (
    ALLOWED_ELIGIBILITY_DECISIONS,
    MatchValidationError,
    build_match_result,
)
from tools.date_validator import has_obvious_expired_signal
from utils.json_handler import JsonHandlerError, parse_json_text
from utils.normalizer import (
    normalize_academic_level,
    normalize_country,
    normalize_language_entries,
    normalize_list,
    normalize_text,
)
from utils.url_utils import first_useful_url


PROMPT_TEMPLATE_PATH = settings.PROJECT_ROOT / "prompts" / "matching.txt"
BROAD_NATIONALITY_TERMS = (
    "international students",
    "all nationalities",
    "all countries",
    "open to all nationalities",
    "students from any country",
    "open to international applicants",
)
LANGUAGE_LEVEL_TOKENS = (
    "a1",
    "a2",
    "b1",
    "b2",
    "c1",
    "c2",
    "ielts",
    "toefl",
    "toeic",
    "cefr",
    "minimum score",
)
FULL_FUNDING_TERMS = (
    "full funding",
    "fully funded",
    "full tuition",
    "tuition and living",
    "stipend",
    "living allowance",
    "covers tuition",
)
PARTIAL_FUNDING_TERMS = (
    "partial",
    "tuition waiver",
    "tuition reduction",
    "discount",
    "fee waiver",
)
FULL_FUNDING_PROFILE_TERMS = (
    "full",
    "fully funded",
    "complete",
    "completa",
)
PARTIAL_FUNDING_PROFILE_TERMS = (
    "partial",
    "parcial",
    "tuition waiver",
)
NO_MODALITY_PREFERENCE_TERMS = {
    "",
    "any",
    "no preference",
    "not specified",
    "unknown",
    "no preference specified",
}
MODALITY_ALIASES = {
    "online": "online",
    "virtual": "online",
    "remote": "online",
    "on-campus": "on-campus",
    "on campus": "on-campus",
    "presencial": "on-campus",
    "in person": "on-campus",
    "hybrid": "hybrid",
    "hibrida": "hybrid",
    "híbrida": "hybrid",
}
INVALID_SOURCE_TYPES = {
    "generic_blog",
    "irrelevant",
    "spam_or_low_quality",
    "expired_or_closed",
}
OFFICIAL_SOURCE_TYPES = {
    "university",
    "institute",
    "institution",
    "government",
    "organization",
    "foundation",
    "company",
    "international_organization",
    "official_pdf",
    "official_university",
    "official_institute",
    "official_institution",
    "official_government",
    "official_organization",
    "official_foundation",
    "official_company",
    "official_announcement",
}
VERIFIED_INFORMATIONAL_SOURCE_TYPES = {
    "verified_news",
    "verified_newspaper",
    "verified_magazine",
    "verified_education_portal",
    "verified_scholarship_information_source",
    "trusted_portal",
}
KNOWN_LANGUAGE_KEYS = (
    "english",
    "spanish",
    "german",
    "french",
    "italian",
    "portuguese",
    "dutch",
    "japanese",
    "korean",
    "chinese",
    "mandarin",
)
ACADEMIC_LEVEL_ALIASES = {
    "high school": "high_school",
    "secondary": "high_school",
    "associate": "associate",
    "undergraduate": "bachelor",
    "bachelor": "bachelor",
    "bachelors": "bachelor",
    "master": "master",
    "masters": "master",
    "graduate": "master",
    "postgraduate": "master",
    "mba": "mba",
    "phd": "phd",
    "doctorate": "phd",
    "doctoral": "phd",
    "postdoc": "postdoc",
}
STEM_TERMS = {
    "stem",
    "computer",
    "science",
    "data",
    "engineering",
    "technology",
    "artificial intelligence",
    "ai",
    "software",
    "machine learning",
    "statistics",
    "informatics",
    "mathematics",
}
LATIN_AMERICA_TERMS = (
    "latin america",
    "latam",
    "south america",
    "america latina",
    "latinoamerica",
)


class MatchingAgent:
    def __init__(self, prompt_template_path: Path = PROMPT_TEMPLATE_PATH) -> None:
        self.prompt_template_path = prompt_template_path
        self.matching_errors: list[dict] = []

    def match_scholarships(
        self, normalized_profile: dict, scholarships: list[dict]
    ) -> list[dict]:
        self.matching_errors = []
        results: list[dict] = []

        for scholarship in scholarships:
            try:
                results.append(self.match_scholarship(normalized_profile, scholarship))
            except (
                MatchValidationError,
                AttributeError,
                TypeError,
                ValueError,
            ) as exc:
                self.matching_errors.append(
                    {
                        "scholarship_name": scholarship.get("scholarship_name"),
                        "source_url": scholarship.get("source_url"),
                        "error": str(exc),
                    }
                )

        return results

    def match_scholarship(self, normalized_profile: dict, scholarship: dict) -> dict:
        evaluation = self._evaluate_deterministically(normalized_profile, scholarship)

        if self._should_use_llm(evaluation):
            llm_result = self._evaluate_with_llm(normalized_profile, scholarship)
            if llm_result is not None:
                evaluation = self._merge_llm_result(evaluation, llm_result)

        match_result = build_match_result(
            scholarship_name=scholarship.get("scholarship_name"),
            source_url=first_useful_url(
                scholarship.get("source_url"),
                scholarship.get("display_link"),
                scholarship.get("official_link"),
                scholarship.get("application_url"),
                scholarship.get("pdf_url"),
            ),
            compatibility_score=evaluation["compatibility_score"],
            eligibility_decision=evaluation["eligibility_decision"],
            matched_factors=evaluation["matched_factors"],
            missing_requirements=evaluation["missing_requirements"],
            risk_factors=evaluation["risk_factors"],
            score_breakdown=evaluation["score_breakdown"],
            recommendation_reason=evaluation["recommendation_reason"],
        )
        match_result.update(
            {
                "display_link": scholarship.get("display_link"),
                "official_link": scholarship.get("official_link"),
                "application_url": scholarship.get("application_url"),
                "pdf_url": scholarship.get("pdf_url"),
                "original_url": scholarship.get("original_url"),
                "query_used": scholarship.get("query_used"),
                "source_type": scholarship.get("source_type"),
            }
        )
        return match_result

    def _evaluate_deterministically(
        self, normalized_profile: dict, scholarship: dict
    ) -> dict:
        profile_nationality = normalize_country(normalized_profile.get("nationality"))
        profile_level = self._normalize_level_key(normalized_profile.get("academic_level"))
        profile_field = normalize_text(normalized_profile.get("field_of_study"))
        profile_interests = normalize_list(normalized_profile.get("interests"))
        profile_countries = {
            country.casefold()
            for country in normalize_list(normalized_profile.get("target_countries"))
        }
        profile_languages = normalize_language_entries(
            normalized_profile.get("languages")
        )
        profile_budget = normalized_profile.get("budget")
        profile_scholarship_type = normalize_text(
            normalized_profile.get("scholarship_type")
        )
        profile_modality = normalize_text(normalized_profile.get("preferred_modality"))

        scholarship_country = normalize_country(scholarship.get("country"))
        scholarship_level = self._normalize_level_key(scholarship.get("academic_level"))
        scholarship_fields = normalize_list(scholarship.get("fields"))
        scholarship_nationalities = normalize_list(
            scholarship.get("eligible_nationalities")
        )
        scholarship_languages = normalize_language_entries(
            scholarship.get("required_languages")
        )
        scholarship_benefits = normalize_list(scholarship.get("benefits"))
        scholarship_type = normalize_text(scholarship.get("scholarship_type"))
        scholarship_modality = normalize_text(
            scholarship.get("modality") or scholarship.get("preferred_modality")
        )

        traceable_link = self._score_traceable_link(scholarship)
        source_validity = self._score_source_validity(scholarship.get("source_type"))
        nationality = self._score_nationality(
            profile_nationality, scholarship_nationalities
        )
        academic = self._score_academic_level(profile_level, scholarship_level)
        field = self._score_field(profile_field, profile_interests, scholarship_fields)
        target_country = self._score_target_country(
            profile_countries, scholarship_country
        )
        language = self._score_language(profile_languages, scholarship_languages)
        funding = self._score_funding(profile_budget, scholarship_benefits)
        scholarship_type_fit = self._score_scholarship_type(
            profile_scholarship_type,
            scholarship_type,
            scholarship_benefits,
        )
        modality = self._score_modality(profile_modality, scholarship_modality)
        source_reliability = self._score_source_reliability(
            scholarship.get("source_reliability_score"),
            scholarship.get("source_type"),
        )
        deadline = self._score_deadline(
            scholarship.get("deadline"),
            scholarship.get("application_status"),
        )

        matched_factors = (
            traceable_link["matched"]
            + source_validity["matched"]
            + nationality["matched"]
            + academic["matched"]
            + field["matched"]
            + target_country["matched"]
            + language["matched"]
            + funding["matched"]
            + scholarship_type_fit["matched"]
            + modality["matched"]
            + source_reliability["matched"]
            + deadline["matched"]
        )
        missing_requirements = (
            traceable_link["missing"]
            + source_validity["missing"]
            + nationality["missing"]
            + academic["missing"]
            + field["missing"]
            + target_country["missing"]
            + language["missing"]
            + funding["missing"]
            + scholarship_type_fit["missing"]
            + modality["missing"]
            + source_reliability["missing"]
            + deadline["missing"]
        )
        risk_factors = (
            traceable_link["risk"]
            + source_validity["risk"]
            + nationality["risk"]
            + academic["risk"]
            + field["risk"]
            + target_country["risk"]
            + language["risk"]
            + funding["risk"]
            + scholarship_type_fit["risk"]
            + modality["risk"]
            + source_reliability["risk"]
            + deadline["risk"]
        )

        score_breakdown = {
            "nationality_score": nationality["score"],
            "academic_level_score": academic["score"],
            "field_score": field["score"],
            "target_country_score": target_country["score"],
            "language_score": language["score"],
            "funding_score": funding["score"],
            "scholarship_type_score": scholarship_type_fit["score"],
            "modality_score": modality["score"],
            "source_reliability_score": source_reliability["score"],
            "deadline_status_score": deadline["score"],
            "link_score": traceable_link["score"],
        }

        compatibility_score = min(
            100,
            max(
                0,
                traceable_link["score"]
                + source_validity["score"]
                + nationality["score"]
                + academic["score"]
                + field["score"]
                + target_country["score"]
                + language["score"]
                + funding["score"]
                + scholarship_type_fit["score"]
                + modality["score"]
                + source_reliability["score"]
                + deadline["score"],
            ),
        )

        if deadline["blocked"]:
            compatibility_score = min(compatibility_score, 35)

        unknown_count = sum(
            int(component["unknown"])
            for component in (
                nationality,
                academic,
                field,
                target_country,
                language,
                funding,
                scholarship_type_fit,
                modality,
                deadline,
            )
        )
        mismatch_count = sum(
            int(component["mismatch"])
            for component in (
                nationality,
                academic,
                field,
                language,
                modality,
            )
        )
        critical_block = (
            traceable_link["blocked"]
            or source_validity["blocked"]
            or deadline["blocked"]
        )

        eligibility_decision = self._choose_decision(
            compatibility_score=compatibility_score,
            missing_requirements=missing_requirements,
            risk_factors=risk_factors,
            unknown_count=unknown_count,
            mismatch_count=mismatch_count,
            critical_block=critical_block,
        )

        recommendation_reason = self._build_recommendation_reason(
            eligibility_decision,
            matched_factors,
            missing_requirements,
            risk_factors,
        )

        return {
            "compatibility_score": compatibility_score,
            "eligibility_decision": eligibility_decision,
            "matched_factors": matched_factors,
            "missing_requirements": missing_requirements,
            "risk_factors": risk_factors,
            "score_breakdown": score_breakdown,
            "recommendation_reason": recommendation_reason,
            "unknown_count": unknown_count,
        }

    def _score_nationality(
        self, profile_nationality: str | None, scholarship_nationalities: list[str]
    ) -> dict:
        if not profile_nationality:
            return self._score_result(
                score=10,
                risk=["User nationality is missing or unknown."],
                unknown=True,
            )

        if not scholarship_nationalities:
            return self._score_result(
                score=14,
                risk=["Eligible nationalities are not clearly specified."],
                unknown=True,
            )

        normalized_options = [item.casefold() for item in scholarship_nationalities]
        nationality_key = profile_nationality.casefold()
        nationality_text = " ".join(normalized_options)

        if any(term in option for option in normalized_options for term in BROAD_NATIONALITY_TERMS):
            return self._score_result(
                score=20,
                matched=["Scholarship appears open to international students."],
            )

        if any(term in nationality_text for term in LATIN_AMERICA_TERMS):
            return self._score_result(
                score=18,
                matched=["Scholarship appears open to Latin American applicants."],
            )

        if any(
            nationality_key == option
            or nationality_key in option
            or option in nationality_key
            for option in normalized_options
        ):
            return self._score_result(
                score=20,
                matched=[f"Nationality appears eligible for {profile_nationality} applicants."],
            )

        if any(term in nationality_text for term in ("except", "excluding", "not open to")):
            return self._score_result(
                score=0,
                missing=[f"Nationality appears explicitly excluded for {profile_nationality} applicants."],
                risk=["Nationality eligibility is a confirmed conflict."],
                mismatch=True,
            )

        return self._score_result(
            score=2,
            missing=[f"Nationality list does not include {profile_nationality} applicants."],
            risk=["Nationality eligibility appears incompatible unless broader rules apply."],
            mismatch=True,
        )

    def _score_academic_level(
        self, profile_level: str | None, scholarship_level: str | None
    ) -> dict:
        if not profile_level:
            return self._score_result(
                score=10,
                risk=["User academic level is missing or unclear."],
                unknown=True,
            )

        if not scholarship_level:
            return self._score_result(
                score=14,
                risk=["Scholarship academic level is not clearly specified."],
                unknown=True,
            )

        if profile_level == scholarship_level:
            return self._score_result(
                score=20,
                matched=["Academic level aligns with the scholarship target level."],
            )

        return self._score_result(
            score=3,
            missing=["Academic level does not match the scholarship target level."],
            risk=["Academic level fit should be checked on the source page."],
            mismatch=True,
        )

    def _score_field(
        self,
        profile_field: str | None,
        profile_interests: list[str],
        scholarship_fields: list[str],
    ) -> dict:
        if not profile_field:
            return self._score_result(
                score=10,
                risk=["User field of study is missing or unclear."],
                unknown=True,
            )

        if not scholarship_fields:
            return self._score_result(
                score=14,
                risk=["Scholarship field restrictions are not clearly specified."],
                unknown=True,
            )

        if self._field_matches(profile_field, profile_interests, scholarship_fields):
            return self._score_result(
                score=20,
                matched=["Field of study is compatible with the scholarship focus."],
            )

        return self._score_result(
            score=6,
            missing=["Field of study does not clearly match the scholarship focus."],
            risk=["Scholarship field coverage may be narrower than the user profile."],
            mismatch=True,
        )

    def _score_target_country(
        self, profile_countries: set[str], scholarship_country: str | None
    ) -> dict:
        if not profile_countries:
            return self._score_result(
                score=10,
                risk=["Target countries are not specified, so country fit is broad."],
                unknown=True,
            )

        if not scholarship_country:
            return self._score_result(
                score=10,
                risk=["Scholarship destination country is unknown."],
                unknown=True,
            )

        if scholarship_country.casefold() in profile_countries:
            return self._score_result(
                score=15,
                matched=["Scholarship country matches a target country preference."],
            )

        return self._score_result(
            score=6,
            risk=["Scholarship country is outside the target country preferences."],
        )

    def _score_language(
        self, profile_languages: list[str], scholarship_languages: list[str]
    ) -> dict:
        if not scholarship_languages:
            return self._score_result(
                score=12,
                risk=["Language requirements are not clearly specified."],
                unknown=True,
            )

        profile_language_keys = {
            self._extract_language_key(language) for language in profile_languages
        }
        profile_language_keys.discard("")

        if not profile_language_keys:
            return self._score_result(
                score=5,
                risk=["User language profile is too limited for a confident check."],
                unknown=True,
            )

        matched: list[str] = []
        missing: list[str] = []
        risk: list[str] = []
        full_matches = 0
        partial_matches = 0

        for requirement in scholarship_languages:
            requirement_key = self._extract_language_key(requirement)
            has_level_signal = self._has_language_level_signal(requirement)

            if requirement_key and requirement_key in profile_language_keys:
                if has_level_signal:
                    partial_matches += 1
                    risk.append(
                        f"Language requirement may need a proficiency level that is not confirmed: {requirement}."
                    )
                else:
                    full_matches += 1
            else:
                missing.append(f"Required language may be missing: {requirement}.")
                risk.append(f"Language requirement needs confirmation: {requirement}.")

        if missing:
            return self._score_result(
                score=7,
                matched=matched,
                missing=missing,
                risk=risk,
                mismatch=True,
            )

        if partial_matches:
            partial_score = {
                "strict": 8,
                "moderate": 10,
                "lenient": 12,
            }.get(settings.MATCHING_LANGUAGE_STRICTNESS, 10)
            return self._score_result(
                score=partial_score,
                matched=["Required languages appear broadly compatible."],
                risk=risk,
            )

        if full_matches:
            matched.append("Required languages align with the user profile.")
            return self._score_result(score=15, matched=matched)

        return self._score_result(
            score=7,
            risk=["Language requirements remain unclear."],
            unknown=True,
        )

    def _score_funding(self, profile_budget: object, scholarship_benefits: list[str]) -> dict:
        if not scholarship_benefits:
            return self._score_result(
                score=4,
                risk=["Funding details are limited or unclear."],
                unknown=True,
            )

        benefits_text = " ".join(scholarship_benefits).casefold()
        contribution_capacity = self._extract_contribution_capacity(profile_budget)

        if any(term in benefits_text for term in FULL_FUNDING_TERMS):
            return self._score_result(
                score=5,
                matched=["Funding coverage looks strong for the user's budget constraints."],
            )

        if any(term in benefits_text for term in PARTIAL_FUNDING_TERMS):
            if contribution_capacity is None:
                return self._score_result(
                    score=3,
                    matched=["Partial funding is mentioned."],
                    risk=["Budget fit needs confirmation because personal contribution is unclear."],
                    unknown=True,
                )

            if contribution_capacity > 0:
                return self._score_result(
                    score=5,
                    matched=["Partial funding may fit the available personal contribution budget."],
                )

            return self._score_result(
                score=1,
                missing=["Partial funding may require personal contribution beyond the available budget."],
                risk=["Budget fit is weak for a partial-funding opportunity."],
            )

        return self._score_result(
            score=2,
            risk=["Funding structure is not explicit enough to confirm budget fit."],
            unknown=True,
        )

    def _score_scholarship_type(
        self,
        profile_scholarship_type: str | None,
        scholarship_type: str | None,
        scholarship_benefits: list[str],
    ) -> dict:
        if not profile_scholarship_type:
            return self._score_result(score=0)

        profile_key = profile_scholarship_type.casefold()
        scholarship_text = " ".join(
            [scholarship_type or "", *scholarship_benefits]
        ).casefold()
        wants_full = any(term in profile_key for term in FULL_FUNDING_PROFILE_TERMS)
        wants_partial = any(term in profile_key for term in PARTIAL_FUNDING_PROFILE_TERMS)

        if wants_full and any(term in scholarship_text for term in FULL_FUNDING_TERMS):
            return self._score_result(
                score=5,
                matched=["Scholarship type appears to match full-funding intent."],
            )

        if wants_partial and any(term in scholarship_text for term in PARTIAL_FUNDING_TERMS):
            return self._score_result(
                score=5,
                matched=["Scholarship type appears to match partial-funding intent."],
            )

        if wants_partial and any(term in scholarship_text for term in FULL_FUNDING_TERMS):
            return self._score_result(
                score=5,
                matched=["Full funding also satisfies partial-funding intent."],
            )

        if wants_full and any(term in scholarship_text for term in PARTIAL_FUNDING_TERMS):
            return self._score_result(
                score=2,
                risk=["Scholarship may offer only partial funding while the user prefers full funding."],
            )

        if scholarship_text and "scholarship" in scholarship_text:
            return self._score_result(
                score=3,
                risk=["Scholarship type is present but funding coverage needs confirmation."],
                unknown=True,
            )

        return self._score_result(
            score=3,
            risk=["Scholarship type or funding coverage is not clearly specified."],
            unknown=True,
        )

    def _score_modality(
        self, profile_modality: str | None, scholarship_modality: str | None
    ) -> dict:
        profile_key = self._normalize_modality(profile_modality)
        if profile_key in NO_MODALITY_PREFERENCE_TERMS:
            return self._score_result(score=0)

        scholarship_key = self._normalize_modality(scholarship_modality)
        if scholarship_key in NO_MODALITY_PREFERENCE_TERMS:
            return self._score_result(
                score=0,
                risk=["Modality is not specified and should be confirmed."],
                unknown=True,
            )

        if profile_key == scholarship_key:
            return self._score_result(
                score=3,
                matched=["Scholarship modality matches the user's preference."],
            )

        if {profile_key, scholarship_key} == {"hybrid", "on-campus"}:
            return self._score_result(
                score=2,
                matched=["Scholarship modality is broadly compatible with the user's preference."],
            )

        return self._score_result(
            score=0,
            risk=["Scholarship modality conflicts with the user's stated preference."],
            mismatch=True,
        )

    def _score_traceable_link(self, scholarship: dict) -> dict:
        display_link = first_useful_url(
            scholarship.get("display_link"),
            scholarship.get("official_link"),
            scholarship.get("application_url"),
            scholarship.get("source_url"),
            scholarship.get("pdf_url"),
        )
        if not display_link:
            return self._score_result(
                score=0,
                missing=["No useful traceable link is available."],
                risk=["Scholarship cannot be traced to a usable source URL."],
                blocked=True,
            )
        return self._score_result(
            score=4,
            matched=["A useful traceable link is available."],
        )

    def _score_source_validity(self, source_type: object) -> dict:
        source_key = normalize_text(source_type).casefold() if source_type else ""
        if source_key in INVALID_SOURCE_TYPES:
            return self._score_result(
                score=0,
                missing=["Source is not acceptable for scholarship evaluation."],
                risk=["Source validation indicates an invalid or unrelated source."],
                blocked=True,
            )
        return self._score_result(score=0)

    def _score_source_reliability(
        self, source_reliability_score: object, source_type: object
    ) -> dict:
        try:
            reliability = int(source_reliability_score)
        except (TypeError, ValueError):
            reliability = 0

        source_key = normalize_text(source_type).casefold() if source_type else ""
        if reliability <= 0 and source_key in OFFICIAL_SOURCE_TYPES:
            reliability = 85
        elif reliability <= 0 and source_key in VERIFIED_INFORMATIONAL_SOURCE_TYPES:
            reliability = 70

        if reliability >= 80:
            return self._score_result(
                score=5,
                matched=["Source reliability is high."],
            )
        if reliability >= 60:
            return self._score_result(
                score=4,
                matched=["Source reliability is reasonably strong."],
            )
        if reliability >= 50:
            return self._score_result(
                score=3,
                risk=["Source reliability is moderate and should be checked carefully."],
            )
        if reliability >= 30:
            return self._score_result(
                score=2,
                risk=["Source reliability is limited."],
            )

        return self._score_result(
            score=0,
            risk=["Source reliability is low or unknown."],
            unknown=True,
        )

    def _score_deadline(self, deadline: object, application_status: object) -> dict:
        status = normalize_text(application_status) or "unknown"
        deadline_text = normalize_text(deadline)

        if status.casefold() == "closed":
            return self._score_result(
                score=0,
                risk=["Applications are marked as closed."],
                missing=["Application status is closed."],
                blocked=True,
            )

        if deadline_text and self._is_expired_deadline(deadline_text):
            return self._score_result(
                score=0,
                risk=["Deadline appears to be expired."],
                missing=["Scholarship deadline appears to have passed."],
                blocked=True,
            )

        if status.casefold() == "upcoming":
            return self._score_result(
                score=4,
                matched=["Application cycle appears upcoming rather than closed."],
            )

        if deadline_text:
            return self._score_result(
                score=5,
                matched=["Deadline information is present and does not appear expired."],
            )

        return self._score_result(
            score=2,
            risk=["Deadline is unknown and needs confirmation."],
            unknown=True,
        )

    def _choose_decision(
        self,
        compatibility_score: int,
        missing_requirements: list[str],
        risk_factors: list[str],
        unknown_count: int,
        mismatch_count: int,
        critical_block: bool,
    ) -> str:
        if critical_block:
            return "rejected"

        if mismatch_count >= 2 and compatibility_score < 60:
            return "mismatch"
        if any(
            text in " ".join(missing_requirements).casefold()
            for text in (
                "nationality list does not include",
                "academic level does not match",
                "field of study does not clearly match",
            )
        ):
            return "mismatch"
        if mismatch_count >= 1 and compatibility_score < 45:
            return "mismatch"

        if (
            compatibility_score >= 85
            and mismatch_count == 0
            and unknown_count <= 1
            and len(missing_requirements) <= 1
        ):
            return "confirmed_match"

        if compatibility_score >= 65 and mismatch_count == 0 and unknown_count <= 3:
            return "likely_match"

        if compatibility_score >= 45 and mismatch_count <= 1:
            return "possible_match"

        if unknown_count >= 4 or (risk_factors and compatibility_score >= 30):
            return "insufficient_information"

        return "mismatch"

    def _should_use_llm(self, evaluation: dict) -> bool:
        return settings.MATCHING_USE_LLM and (
            evaluation["eligibility_decision"] == "insufficient_information"
            or (
                evaluation["eligibility_decision"] in {"possible_match", "likely_match"}
                and evaluation["unknown_count"] >= 2
            )
        )

    def _evaluate_with_llm(
        self, normalized_profile: dict, scholarship: dict
    ) -> dict | None:
        prompt = self._build_prompt(normalized_profile, scholarship)
        try:
            response = generate_text(prompt)
            payload = parse_json_text(response)
            eligibility_decision = normalize_text(payload.get("eligibility_decision"))
            if eligibility_decision not in ALLOWED_ELIGIBILITY_DECISIONS:
                return None
            return {
                "eligibility_decision": eligibility_decision,
                "matched_factors": normalize_list(payload.get("matched_factors")),
                "missing_requirements": normalize_list(
                    payload.get("missing_requirements")
                ),
                "risk_factors": normalize_list(payload.get("risk_factors")),
                "recommendation_reason": normalize_text(
                    payload.get("recommendation_reason")
                )
                or "",
            }
        except (
            LLMProviderError,
            JsonHandlerError,
            TypeError,
            ValueError,
        ):
            return None

    def _merge_llm_result(self, evaluation: dict, llm_result: dict) -> dict:
        merged = dict(evaluation)
        merged["eligibility_decision"] = llm_result["eligibility_decision"]
        merged["matched_factors"] = llm_result["matched_factors"] or evaluation[
            "matched_factors"
        ]
        merged["missing_requirements"] = llm_result["missing_requirements"] or evaluation[
            "missing_requirements"
        ]
        merged["risk_factors"] = llm_result["risk_factors"] or evaluation["risk_factors"]
        merged["recommendation_reason"] = llm_result["recommendation_reason"] or evaluation[
            "recommendation_reason"
        ]
        return merged

    def _build_prompt(self, normalized_profile: dict, scholarship: dict) -> str:
        template = self.prompt_template_path.read_text(encoding="utf-8").strip()
        payload = {
            "normalized_profile": normalized_profile,
            "scholarship": {
                "scholarship_name": scholarship.get("scholarship_name"),
                "institution": scholarship.get("institution"),
                "country": scholarship.get("country"),
                "academic_level": scholarship.get("academic_level"),
                "eligible_nationalities": scholarship.get("eligible_nationalities"),
                "required_languages": scholarship.get("required_languages"),
                "fields": scholarship.get("fields"),
                "benefits": scholarship.get("benefits"),
                "deadline": scholarship.get("deadline"),
                "requirements": scholarship.get("requirements"),
                "application_status": scholarship.get("application_status"),
                "source_url": scholarship.get("source_url"),
                "source_type": scholarship.get("source_type"),
                "source_reliability_score": scholarship.get("source_reliability_score"),
                "evidence_snippets": scholarship.get("evidence_snippets"),
            },
        }
        payload_json = json.dumps(payload, indent=2, ensure_ascii=False)
        return f"{template}\n\nMatching input:\n{payload_json}"

    def _field_matches(
        self,
        profile_field: str,
        profile_interests: list[str],
        scholarship_fields: list[str],
    ) -> bool:
        scholarship_text = " ".join(scholarship_fields).casefold()
        profile_field_key = profile_field.casefold()
        interest_keys = [interest.casefold() for interest in profile_interests]

        if profile_field_key in scholarship_text:
            return True
        if any(field.casefold() in profile_field_key for field in scholarship_fields):
            return True
        if any(interest in scholarship_text for interest in interest_keys):
            return True

        return self._is_stem_related(profile_field_key) and self._is_stem_related(
            scholarship_text
        )

    def _normalize_level_key(self, value: object) -> str | None:
        normalized_value = normalize_academic_level(value)
        if not normalized_value:
            return None
        comparison_value = normalized_value.casefold()
        return ACADEMIC_LEVEL_ALIASES.get(comparison_value, comparison_value)

    def _normalize_modality(self, value: object) -> str:
        normalized_value = normalize_text(value)
        if not normalized_value:
            return ""
        comparison_value = normalized_value.casefold()
        return MODALITY_ALIASES.get(comparison_value, comparison_value)

    def _is_stem_related(self, text: str) -> bool:
        return any(term in text for term in STEM_TERMS)

    def _extract_language_key(self, value: str) -> str:
        lowered = value.casefold()
        for language_key in KNOWN_LANGUAGE_KEYS:
            if language_key in lowered:
                return language_key
        return lowered.strip()

    def _has_language_level_signal(self, value: str) -> bool:
        lowered = value.casefold()
        return any(token in lowered for token in LANGUAGE_LEVEL_TOKENS)

    def _extract_contribution_capacity(self, budget: object) -> float | None:
        if isinstance(budget, (int, float)):
            return float(budget)

        if isinstance(budget, dict):
            value = budget.get("max_personal_contribution")
            if isinstance(value, (int, float)):
                return float(value)

        return None

    def _is_expired_deadline(self, deadline_text: str) -> bool:
        if has_obvious_expired_signal(deadline_text, ""):
            return True

        deadline_formats = (
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
        )

        for date_format in deadline_formats:
            try:
                parsed_date = datetime.strptime(deadline_text, date_format).date()
                return parsed_date < datetime.now(timezone.utc).date()
            except ValueError:
                continue

        if deadline_text.isdigit() and len(deadline_text) == 4:
            try:
                return int(deadline_text) < datetime.now(timezone.utc).year
            except ValueError:
                return False

        return False

    def _build_recommendation_reason(
        self,
        eligibility_decision: str,
        matched_factors: list[str],
        missing_requirements: list[str],
        risk_factors: list[str],
    ) -> str:
        if eligibility_decision in {"confirmed_match", "strong_match"}:
            return "Profile aligns well with the core eligibility and preference factors."
        if eligibility_decision == "likely_match":
            if risk_factors:
                return f"Profile is a good fit, but {risk_factors[0].rstrip('.').lower()}."
            return "Profile aligns with the main scholarship signals, with a few details to confirm."
        if eligibility_decision == "possible_match":
            if risk_factors:
                return f"Overall fit looks promising, but {risk_factors[0].rstrip('.').lower()}."
            return "Profile aligns with several key factors, with some details still needing confirmation."
        if eligibility_decision in {"mismatch", "weak_match"}:
            if missing_requirements:
                return f"Fit is limited because {missing_requirements[0].rstrip('.').lower()}."
            return "Fit is uncertain and only a few compatibility signals are present."
        if eligibility_decision in {"rejected", "not_eligible"}:
            if missing_requirements:
                return f"Current information suggests the user is not eligible because {missing_requirements[0].rstrip('.').lower()}."
            return "Current information suggests the scholarship is not a viable option."
        if matched_factors:
            return "Some compatibility signals are present, but important eligibility details remain unclear."
        return "The available scholarship data is too incomplete for a confident recommendation."

    def _score_result(
        self,
        score: int,
        matched: list[str] | None = None,
        missing: list[str] | None = None,
        risk: list[str] | None = None,
        blocked: bool = False,
        unknown: bool = False,
        mismatch: bool = False,
    ) -> dict:
        return {
            "score": max(0, int(score)),
            "matched": matched or [],
            "missing": missing or [],
            "risk": risk or [],
            "blocked": blocked,
            "unknown": unknown,
            "mismatch": mismatch,
        }
