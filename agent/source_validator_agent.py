from __future__ import annotations

import json
from pathlib import Path

from config.settings import settings
from database.repository import get_untrusted_source_match, save_untrusted_source
from llm.provider import LLMProviderError, generate_text
from schemas.source_schema import SourceValidationError, build_validated_source
from tools.date_validator import has_obvious_expired_signal
from utils.json_handler import JsonHandlerError, parse_json_text
from utils.url_utils import extract_domain, has_suspicious_domain


PROMPT_TEMPLATE_PATH = settings.PROJECT_ROOT / "prompts" / "source_validation.txt"

SCHOLARSHIP_TERMS = (
    "scholarship",
    "scholarships",
    "bourse",
    "bursary",
    "grant",
    "grants",
    "fellowship",
    "fellowships",
    "financial aid",
    "financial support",
    "funding",
    "award",
    "stipend",
    "stipendium",
    "studentship",
    "tuition waiver",
    "tuition waivers",
)

BLOG_OR_MEDIA_TERMS = (
    "blog",
    "linkedin",
    "medium",
    "substack",
    "wordpress",
    "blogspot",
)

TRUSTED_PORTAL_DOMAINS = (
    "educanada.ca",
    "studyinnl.org",
    "studyinholland.nl",
    "daad.de",
    "campusfrance.org",
    "scholarshipportal.com",
    "bachelorsportal.com",
    "mastersportal.com",
)

OFFICIAL_ORGANIZATION_DOMAINS = (
    "nuffic.nl",
    "colfuturo.org",
    "fulbright",
    "erasmus",
    "britishcouncil",
    "daad.de",
)

SCHOLARSHIP_DATABASE_DOMAINS = (
    "scholarshipsads.com",
    "scholarshiptab.com",
    "scholarshipca.com",
    "globalscholarships.com",
    "fullyfundedscholarship.org",
    "opportunitiesforyouth.org",
    "scholarshiproar.com",
    "scholarshipregion.com",
    "youthopportunitieshub.com",
)

COPIED_AGGREGATOR_TERMS = (
    "copied scholarship",
    "scholarship listing",
    "list of scholarships",
    "top scholarships",
    "fully funded scholarships 202",
)

OFFICIAL_GOVERNMENT_DOMAINS = (
    "canada.ca",
    "gc.ca",
    "europa.eu",
)
OFFICIAL_COMPANY_DOMAINS = (
    "google.",
    "microsoft.",
    "amazon.",
    "ibm.",
    "nvidia.",
    "adobe.",
    "intel.",
    "meta.",
    "apple.",
    "openai.",
)
VERIFIED_NEWS_DOMAINS = (
    "timeshighereducation.com",
    "universityworldnews.com",
    "insidehighered.com",
    "chronicle.com",
    "bbc.com",
    "bbc.co.uk",
    "theguardian.com",
    "dw.com",
    "elpais.com",
    "reuters.com",
    "apnews.com",
)
NEWS_OR_MAGAZINE_DOMAIN_TERMS = (
    "news",
    "magazine",
    "newspaper",
    "times",
    "chronicle",
)
GOVERNMENT_TEXT_TERMS = (
    "government",
    "ministry",
    "embassy",
    "consulate",
    "department of education",
    "secretariat",
)
UNIVERSITY_TEXT_TERMS = (
    "university",
    "college",
    "school of",
)
INSTITUTE_TEXT_TERMS = (
    "institute",
    "research center",
    "research centre",
)
FOUNDATION_TEXT_TERMS = (
    "foundation",
)
PROFESSIONAL_ASSOCIATION_TERMS = (
    "professional association",
    "association scholarship",
    "society scholarship",
    "association of",
    "computer society",
    "ieee",
    "acm",
)
INTERNATIONAL_ORGANIZATION_TERMS = (
    "united nations",
    "world bank",
    "unesco",
    "oecd",
    "organization of american states",
    "oas",
    "international organization",
)
SECONDARY_INFORMATIONAL_TYPES = {
    "verified_news",
    "verified_newspaper",
    "verified_magazine",
    "verified_education_portal",
    "verified_scholarship_information_source",
}
DIRECT_TRUSTED_TYPES = {
    "university",
    "government",
    "embassy",
    "international_organization",
    "recognized_foundation",
    "official_company",
    "professional_association",
    "official_pdf",
}
CLEARLY_UNTRUSTED_TYPES = {
    "generic_blog",
    "copied_aggregator",
    "spam",
    "spam_or_low_quality",
    "unknown_unverified",
}


class SourceValidatorAgent:
    def __init__(
        self,
        prompt_template_path: Path = PROMPT_TEMPLATE_PATH,
        db_path: str | Path | None = None,
    ) -> None:
        self.prompt_template_path = prompt_template_path
        self.db_path = db_path

    def validate_sources(self, candidate_results: list[dict]) -> list[dict]:
        return [self.validate_source(result) for result in candidate_results]

    def validate_source(self, candidate_result: dict) -> dict:
        deterministic_result = self._classify_deterministically(candidate_result)
        if self._should_use_llm(deterministic_result):
            llm_result = self._classify_with_llm(candidate_result)
            if llm_result is not None:
                return llm_result

        return deterministic_result

    def _classify_deterministically(self, candidate_result: dict) -> dict:
        title = str(candidate_result.get("title") or "").strip()
        url = str(candidate_result.get("url") or "").strip()
        snippet = str(candidate_result.get("snippet") or "").strip()
        query = str(candidate_result.get("query") or "").strip()
        domain = extract_domain(url)
        candidate_with_metadata = dict(candidate_result)
        if domain is not None:
            candidate_with_metadata.setdefault("source_domain", domain)
        candidate_with_metadata.setdefault("query_used", candidate_result.get("query_used") or query)

        reasons: list[str] = []
        risk_flags: list[str] = []

        if not title or not url or domain is None:
            return build_validated_source(
                candidate_with_metadata,
                "spam",
                0,
                0,
                "reject",
                ["Missing title or valid URL."],
                ["malformed_or_missing_url"],
            )

        known_untrusted = get_untrusted_source_match(url, domain, db_path=self.db_path)
        if known_untrusted is not None:
            return build_validated_source(
                candidate_with_metadata,
                known_untrusted.get("source_type") or "unknown_unverified",
                0,
                0,
                "reject",
                ["known_untrusted_source"],
                ["known_untrusted_source"],
            )

        if has_obvious_expired_signal(title, snippet):
            return build_validated_source(
                candidate_with_metadata,
                "expired_or_closed",
                20,
                20,
                "reject",
                ["Result has obvious expired or closed application signals."],
                ["expired_or_closed"],
            )

        if not self._has_scholarship_signal(title, snippet):
            return build_validated_source(
                candidate_with_metadata,
                "non_scholarship_page",
                20,
                10,
                "reject",
                ["Result does not mention scholarships, funding, or financial aid."],
                ["low_relevance"],
            )

        relevance_score = self._score_relevance(title, snippet, query)
        if relevance_score < 25:
            return build_validated_source(
                candidate_with_metadata,
                "non_scholarship_page",
                20,
                relevance_score,
                "reject",
                ["Result does not appear related to scholarships or funding."],
                ["low_relevance"],
            )

        source_type, reliability_score = self._score_reliability(
            domain,
            url,
            title,
            snippet,
            str(candidate_result.get("source_type") or ""),
            str(candidate_result.get("source_family") or ""),
        )
        reasons.append(f"Domain classified as {source_type}.")
        risk_flags.append("source_type_inferred")

        if has_suspicious_domain(url):
            risk_flags.append("suspicious_or_media_domain")
            if source_type in {"unknown", "unknown_unverified"}:
                source_type = "generic_blog"
                reliability_score = min(reliability_score, 35)

        if any(term in domain for term in BLOG_OR_MEDIA_TERMS):
            risk_flags.append("blog_or_media_domain")
            source_type = "generic_blog"
            reliability_score = min(reliability_score, 35)

        if not self._has_deadline_signal(title, snippet):
            risk_flags.append("deadline_unknown")
        if source_type in SECONDARY_INFORMATIONAL_TYPES:
            risk_flags.extend(
                [
                    "informational_source",
                    "secondary_guidance_only",
                    "official_call_not_confirmed",
                ]
            )
        if source_type not in {
            "non_scholarship_page",
            "expired_or_closed",
            "spam",
            "spam_or_low_quality",
        }:
            risk_flags.append("requirements_incomplete")
        reasons[0] = f"Domain classified as {source_type}."

        decision = self._choose_decision(
            source_type,
            reliability_score,
            relevance_score,
            risk_flags,
        )

        validated_source = build_validated_source(
            candidate_with_metadata,
            source_type,
            reliability_score,
            relevance_score,
            decision,
            reasons,
            risk_flags,
        )
        self._remember_untrusted_if_needed(validated_source)
        return validated_source

    def _score_reliability(
        self,
        domain: str,
        url: str,
        title: str,
        snippet: str,
        candidate_source_type: str,
        candidate_source_family: str = "",
    ) -> tuple[str, int]:
        lowered_url = url.casefold()
        text = f"{title} {snippet} {url} {domain}".casefold()
        preliminary_type = candidate_source_type.strip().casefold()
        preliminary_family = candidate_source_family.strip().casefold()

        if self._looks_like_copied_aggregator(domain, text):
            return "copied_aggregator", 25

        if lowered_url.endswith(".pdf") and self._looks_official_domain(domain, text):
            return "official_pdf", 82
        if "embassy" in text or "consulate" in text or preliminary_family == "embassy":
            return "embassy", 88
        if any(domain.endswith(pattern) for pattern in OFFICIAL_GOVERNMENT_DOMAINS):
            return "government", 95
        if domain.endswith((".gov", ".gov.uk", ".gov.ca", ".gov.au", ".gouv.fr")):
            return "government", 95
        if any(term in text for term in GOVERNMENT_TEXT_TERMS):
            return "government", 88
        if domain.endswith((".edu", ".edu.au", ".edu.co", ".edu.mx", ".edu.sg", ".ac.uk", ".ac.jp")):
            return "university", 90
        if domain.endswith((".ac.", ".edu.")):
            return "institution", 85
        if any(term in text for term in UNIVERSITY_TEXT_TERMS):
            return "university", 82
        if any(term in text for term in INTERNATIONAL_ORGANIZATION_TERMS):
            return "international_organization", 82
        if any(term in text for term in INSTITUTE_TEXT_TERMS):
            return "institute", 78
        if any(domain.endswith(pattern) for pattern in SCHOLARSHIP_DATABASE_DOMAINS):
            return "copied_aggregator", 35
        if any(term in text for term in FOUNDATION_TEXT_TERMS):
            return "recognized_foundation", 78
        if any(pattern in domain for pattern in OFFICIAL_ORGANIZATION_DOMAINS):
            return "organization", 80
        if any(pattern in domain for pattern in OFFICIAL_COMPANY_DOMAINS):
            return "official_company", 78
        if any(term in text for term in PROFESSIONAL_ASSOCIATION_TERMS):
            return "professional_association", 78
        if any(domain.endswith(pattern) for pattern in TRUSTED_PORTAL_DOMAINS):
            return "verified_education_portal", 70
        if any(domain.endswith(pattern) for pattern in VERIFIED_NEWS_DOMAINS):
            return self._verified_media_type(domain), 68
        if any(term in domain for term in NEWS_OR_MAGAZINE_DOMAIN_TERMS):
            return "verified_news", 58
        if preliminary_type in {
            "university",
            "government",
            "embassy",
            "organization",
            "foundation",
            "recognized_foundation",
            "institute",
            "company",
            "official_company",
            "international_organization",
            "professional_association",
            "verified_news",
        }:
            return self._canonical_preliminary_type(preliminary_type), 60
        if domain.endswith(".org"):
            return "organization", 65
        return "unknown_unverified", 45

    def _score_relevance(self, title: str, snippet: str, query: str) -> int:
        text = f"{title} {snippet}".casefold()
        query_terms = {
            token
            for token in query.casefold().replace("site:", " ").split()
            if len(token) > 3
        }

        score = 20
        if any(term in text for term in SCHOLARSHIP_TERMS):
            score += 45
        if "student" in text or "international" in text:
            score += 10
        if "computer" in text or "science" in text or "data" in text:
            score += 10
        if query_terms:
            matched_terms = sum(1 for term in query_terms if term in text)
            score += min(15, matched_terms * 3)

        return min(score, 100)

    def _has_scholarship_signal(self, title: str, snippet: str) -> bool:
        text = f"{title} {snippet}".casefold()
        return any(term in text for term in SCHOLARSHIP_TERMS)

    def _has_deadline_signal(self, title: str, snippet: str) -> bool:
        text = f"{title} {snippet}".casefold()
        return any(
            term in text
            for term in (
                "deadline",
                "apply by",
                "applications open",
                "applications close",
                "open now",
                "2025",
                "2026",
                "2027",
            )
        )

    def _choose_decision(
        self,
        source_type: str,
        reliability_score: int,
        relevance_score: int,
        risk_flags: list[str],
    ) -> str:
        if source_type in {
            "non_scholarship_page",
            "irrelevant",
            "spam",
            "spam_or_low_quality",
            "expired_or_closed",
            "generic_blog",
            "scholarship_database",
            "copied_aggregator",
            "unknown",
            "unknown_unverified",
        }:
            return "reject"
        if reliability_score < 30 or relevance_score < 25:
            return "reject"
        if source_type in SECONDARY_INFORMATIONAL_TYPES:
            return "review"
        hard_risk_flags = {
            "suspicious_or_media_domain",
            "blog_or_media_domain",
        }
        if hard_risk_flags.intersection(risk_flags):
            return "reject"
        if reliability_score < settings.SOURCE_VALIDATION_MIN_RELIABILITY:
            return "review"
        if relevance_score < settings.SOURCE_VALIDATION_MIN_RELEVANCE:
            return "review"
        return "accept"

    def _should_use_llm(self, validated_source: dict) -> bool:
            return (
                settings.SOURCE_VALIDATION_USE_LLM
            and validated_source["decision"] == "review"
            and validated_source["source_type"] == "unknown_unverified"
        )

    def _classify_with_llm(self, candidate_result: dict) -> dict | None:
        prompt = self._build_prompt(candidate_result)
        try:
            response = generate_text(prompt)
            payload = parse_json_text(response)
            return build_validated_source(
                candidate_result,
                str(payload.get("source_type")),
                int(payload.get("reliability_score", 0)),
                int(payload.get("relevance_score", 0)),
                str(payload.get("decision")),
                list(payload.get("reasons", [])),
                list(payload.get("risk_flags", [])),
            )
        except (
            LLMProviderError,
            JsonHandlerError,
            SourceValidationError,
            TypeError,
            ValueError,
        ):
            return None

    def _build_prompt(self, candidate_result: dict) -> str:
        template = self.prompt_template_path.read_text(encoding="utf-8").strip()
        result_json = json.dumps(candidate_result, indent=2, ensure_ascii=False)
        return f"{template}\n\nCandidate result:\n{result_json}"

    def _looks_official_domain(self, domain: str, text: str) -> bool:
        if domain.endswith((".edu", ".gov", ".org", ".ac.uk", ".gouv.fr")):
            return True
        return any(
            term in text
            for term in (
                *GOVERNMENT_TEXT_TERMS,
                *UNIVERSITY_TEXT_TERMS,
                *INSTITUTE_TEXT_TERMS,
                *FOUNDATION_TEXT_TERMS,
                "organization",
            )
        )

    def _canonical_preliminary_type(self, source_type: str) -> str:
        mapping = {
            "foundation": "recognized_foundation",
            "company": "official_company",
        }
        return mapping.get(source_type, source_type)

    def _looks_like_copied_aggregator(self, domain: str, text: str) -> bool:
        if any(domain.endswith(pattern) for pattern in SCHOLARSHIP_DATABASE_DOMAINS):
            return True
        return any(term in text for term in COPIED_AGGREGATOR_TERMS)

    def _remember_untrusted_if_needed(self, validated_source: dict) -> None:
        if validated_source.get("decision") != "reject":
            return
        source_type = str(validated_source.get("source_type") or "")
        risk_flags = set(validated_source.get("risk_flags") or [])
        if source_type not in CLEARLY_UNTRUSTED_TYPES and not {
            "suspicious_or_media_domain",
            "blog_or_media_domain",
        }.intersection(risk_flags):
            return
        save_untrusted_source(
            validated_source.get("url"),
            validated_source.get("source_domain"),
            validated_source.get("validation_reason") or "Source rejected.",
            source_type,
            db_path=self.db_path,
        )

    def _verified_media_type(self, domain: str) -> str:
        if "timeshighereducation" in domain or "chronicle" in domain:
            return "verified_magazine"
        if "guardian" in domain or "elpais" in domain:
            return "verified_newspaper"
        return "verified_news"
