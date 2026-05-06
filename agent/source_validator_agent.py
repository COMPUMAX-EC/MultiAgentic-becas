from __future__ import annotations

import json
from pathlib import Path

from config.settings import settings
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
    "financial aid",
    "funding",
    "award",
    "stipend",
    "stipendium",
)

BLOG_OR_MEDIA_TERMS = (
    "blog",
    "news",
    "linkedin",
    "medium",
    "substack",
    "wordpress",
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
)

OFFICIAL_GOVERNMENT_DOMAINS = (
    "canada.ca",
    "gc.ca",
    "europa.eu",
)


class SourceValidatorAgent:
    def __init__(self, prompt_template_path: Path = PROMPT_TEMPLATE_PATH) -> None:
        self.prompt_template_path = prompt_template_path

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

        reasons: list[str] = []
        risk_flags: list[str] = []

        if not title or not url or domain is None:
            return build_validated_source(
                candidate_result,
                "spam_or_low_quality",
                0,
                0,
                "reject",
                ["Missing title or valid URL."],
                ["malformed_or_missing_url"],
            )

        if has_obvious_expired_signal(title, snippet):
            return build_validated_source(
                candidate_result,
                "expired_or_closed",
                20,
                20,
                "reject",
                ["Result has obvious expired or closed application signals."],
                ["expired_or_closed"],
            )

        if not self._has_scholarship_signal(title, snippet):
            return build_validated_source(
                candidate_result,
                "irrelevant",
                20,
                10,
                "reject",
                ["Result does not mention scholarships, funding, or financial aid."],
                ["low_relevance"],
            )

        relevance_score = self._score_relevance(title, snippet, query)
        if relevance_score < 25:
            return build_validated_source(
                candidate_result,
                "irrelevant",
                20,
                relevance_score,
                "reject",
                ["Result does not appear related to scholarships or funding."],
                ["low_relevance"],
            )

        source_type, reliability_score = self._score_reliability(domain)
        reasons.append(f"Domain classified as {source_type}.")

        if has_suspicious_domain(url):
            risk_flags.append("suspicious_or_media_domain")
            if source_type == "uncertain_source":
                source_type = "blog_or_media"
                reliability_score = min(reliability_score, 35)

        if any(term in domain for term in BLOG_OR_MEDIA_TERMS):
            risk_flags.append("blog_or_media_domain")
            source_type = "blog_or_media"
            reliability_score = min(reliability_score, 35)

        decision = self._choose_decision(
            source_type,
            reliability_score,
            relevance_score,
            risk_flags,
        )

        return build_validated_source(
            candidate_result,
            source_type,
            reliability_score,
            relevance_score,
            decision,
            reasons,
            risk_flags,
        )

    def _score_reliability(self, domain: str) -> tuple[str, int]:
        if any(domain.endswith(pattern) for pattern in OFFICIAL_GOVERNMENT_DOMAINS):
            return "official_government", 95
        if domain.endswith((".gov", ".gov.uk", ".gov.ca", ".gov.au", ".gouv.fr")):
            return "official_government", 95
        if domain.endswith((".edu", ".edu.au", ".edu.co", ".ac.uk")):
            return "official_university", 90
        if any(pattern in domain for pattern in OFFICIAL_ORGANIZATION_DOMAINS):
            return "official_organization", 80
        if any(domain.endswith(pattern) for pattern in TRUSTED_PORTAL_DOMAINS):
            return "trusted_portal", 70
        if any(domain.endswith(pattern) for pattern in SCHOLARSHIP_DATABASE_DOMAINS):
            return "scholarship_database", 55
        if domain.endswith(".org"):
            return "official_organization", 65
        return "uncertain_source", 45

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

    def _choose_decision(
        self,
        source_type: str,
        reliability_score: int,
        relevance_score: int,
        risk_flags: list[str],
    ) -> str:
        if source_type in {"irrelevant", "spam_or_low_quality", "expired_or_closed"}:
            return "reject"
        if reliability_score < 30 or relevance_score < 25:
            return "reject"
        if risk_flags or reliability_score < settings.SOURCE_VALIDATION_MIN_RELIABILITY:
            return "review"
        if relevance_score < settings.SOURCE_VALIDATION_MIN_RELEVANCE:
            return "review"
        return "accept"

    def _should_use_llm(self, validated_source: dict) -> bool:
        return (
            settings.SOURCE_VALIDATION_USE_LLM
            and validated_source["decision"] == "review"
            and validated_source["source_type"] == "uncertain_source"
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
