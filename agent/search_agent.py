from __future__ import annotations

from urllib.parse import urlsplit

from config.settings import settings
from schemas.search_schema import validate_search_results
from tools.web_search import WebSearchError, search_web
from utils.deduplicator import normalize_url
from utils.logger import get_logger


logger = get_logger(__name__)


class SearchAgent:
    def __init__(self) -> None:
        self.last_raw_results_count = 0
        self.last_deduplicated_count = 0
        self.search_errors: list[dict] = []

    def search(self, generated_queries: list[dict]) -> list[dict]:
        aggregated_results: list[dict] = []
        self.last_raw_results_count = 0
        self.last_deduplicated_count = 0
        self.search_errors = []

        for query_object in generated_queries[: settings.SEARCH_MAX_QUERIES]:
            query_text = query_object["query"]
            query_used = query_text
            try:
                query_results = search_web(query_text)
            except WebSearchError as exc:
                logger.warning("Search failed for query '%s': %s", query_text, exc)
                self.search_errors.append({"query": query_text, "error": str(exc)})
                continue

            if not query_results:
                fallback_query = self._build_fallback_query(query_text)
                if fallback_query and fallback_query != query_text:
                    logger.info(
                        "Retrying query with simplified search text: %s", fallback_query
                    )
                    try:
                        query_results = search_web(fallback_query)
                        query_used = fallback_query
                    except WebSearchError as exc:
                        logger.warning(
                            "Fallback search failed for query '%s': %s",
                            fallback_query,
                            exc,
                        )
                        self.search_errors.append(
                            {"query": fallback_query, "error": str(exc)}
                        )
                        query_results = []

            limited_results = query_results[: settings.SEARCH_MAX_RESULTS_PER_QUERY]
            self.last_raw_results_count += len(limited_results)
            for result in limited_results:
                url = result.get("url")
                source_domain = self._source_domain(url)
                aggregated_results.append(
                    {
                        "title": result.get("title"),
                        "url": url,
                        "canonical_url": result.get("canonical_url") or url,
                        "snippet": result.get("snippet"),
                        "source": result.get("source"),
                        "query": query_text,
                        "query_used": query_used,
                        "target_country": query_object.get("target_country"),
                        "priority": query_object.get("priority"),
                        "source_domain": source_domain,
                        "source_type": self._infer_source_type(
                            result,
                            source_domain,
                            query_text,
                        ),
                    }
                )

        validated_results = validate_search_results(aggregated_results)
        deduplicated_results = self._deduplicate_candidates(validated_results)
        limited_candidates = deduplicated_results[: settings.SEARCH_MAX_GLOBAL_CANDIDATES]
        self.last_deduplicated_count = len(limited_candidates)
        return limited_candidates

    def _build_fallback_query(self, query_text: str) -> str:
        removable_tokens = {
            "official",
            "government",
            "government-funded",
            "foundation",
            "portal",
        }
        simplified_tokens: list[str] = []

        for token in query_text.split():
            lowered_token = token.lower()
            if lowered_token.startswith("site:"):
                continue
            if lowered_token in removable_tokens:
                continue
            simplified_tokens.append(token)

        return " ".join(simplified_tokens)

    def _deduplicate_candidates(self, results: list[dict]) -> list[dict]:
        deduplicated_results: list[dict] = []
        seen_candidate_keys: set[str] = set()

        for result in results:
            candidate_key = self._candidate_key(result)
            if candidate_key in seen_candidate_keys:
                continue
            seen_candidate_keys.add(candidate_key)
            deduplicated_results.append(result)

        return deduplicated_results

    def _candidate_key(self, result: dict) -> str:
        canonical_url = result.get("canonical_url") or result.get("url")
        if isinstance(canonical_url, str) and canonical_url.strip():
            return f"url:{normalize_url(canonical_url)}"

        title = " ".join(str(result.get("title") or "").casefold().split())
        domain = str(result.get("source_domain") or "").casefold()
        return f"title-domain:{title}:{domain}"

    def _source_domain(self, url: object) -> str:
        if not isinstance(url, str) or not url.strip():
            return ""
        return urlsplit(url).netloc.lower().removeprefix("www.")

    def _infer_source_type(
        self,
        result: dict,
        source_domain: str,
        query_text: str,
    ) -> str:
        haystack = " ".join(
            str(value or "")
            for value in (
                result.get("title"),
                result.get("snippet"),
                result.get("url"),
                source_domain,
                query_text,
            )
        ).casefold()

        if ".edu" in source_domain or "university" in haystack:
            return "university"
        if ".gov" in source_domain or "government" in haystack or "ministry" in haystack:
            return "government"
        if "foundation" in haystack:
            return "foundation"
        if "institute" in haystack or "research center" in haystack:
            return "institute"
        if ".org" in source_domain or "organization" in haystack:
            return "organization"
        if "company" in haystack or "corporate" in haystack or "technology" in haystack:
            return "company"
        if self._looks_like_verified_news(source_domain, haystack):
            return "verified_news"
        return "unknown"

    def _looks_like_verified_news(self, source_domain: str, haystack: str) -> bool:
        news_terms = {
            "news",
            "newspaper",
            "magazine",
            "times",
            "post",
            "guardian",
            "bbc",
            "reuters",
        }
        return any(term in source_domain or term in haystack for term in news_terms)
