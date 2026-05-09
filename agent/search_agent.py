from __future__ import annotations

from collections import defaultdict
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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
        self.last_expansion_rounds_used = 0
        self.search_errors: list[dict] = []

    def search(self, generated_queries: list[dict]) -> list[dict]:
        aggregated_results: list[dict] = []
        self.last_raw_results_count = 0
        self.last_deduplicated_count = 0
        self.last_expansion_rounds_used = 0
        self.search_errors = []
        executed_queries = 0
        max_queries = getattr(settings, "SEARCH_MAX_QUERIES", 30)
        max_expansion_rounds = getattr(settings, "MAX_EXPANSION_ROUNDS", 0)
        minimum_candidates = getattr(
            settings,
            "MIN_RECOMMENDED_RESULTS_BEFORE_EXPANSION",
            5,
        )

        queries_by_round = self._queries_by_expansion_round(generated_queries)
        for expansion_round in sorted(queries_by_round):
            if expansion_round > max_expansion_rounds:
                continue
            if expansion_round > 0:
                current_candidates = self._deduplicate_candidates(
                    validate_search_results(aggregated_results)
                )
                if len(current_candidates) >= minimum_candidates:
                    break
                self.last_expansion_rounds_used = expansion_round

            for query_object in queries_by_round[expansion_round]:
                if executed_queries >= max_queries:
                    break
                aggregated_results.extend(self._collect_query_results(query_object))
                executed_queries += 1

            if executed_queries >= max_queries:
                break

        validated_results = validate_search_results(aggregated_results)
        deduplicated_results = self._deduplicate_candidates(validated_results)
        limited_candidates = deduplicated_results[: settings.SEARCH_MAX_GLOBAL_CANDIDATES]
        self.last_deduplicated_count = len(limited_candidates)
        return limited_candidates

    def _queries_by_expansion_round(self, generated_queries: list[dict]) -> dict[int, list[dict]]:
        queries_by_round: dict[int, list[dict]] = defaultdict(list)
        for query_object in generated_queries:
            try:
                expansion_round = int(query_object.get("expansion_round", 0) or 0)
            except (TypeError, ValueError):
                expansion_round = 0
            queries_by_round[max(0, expansion_round)].append(query_object)
        return dict(queries_by_round)

    def _collect_query_results(self, query_object: dict) -> list[dict]:
        query_text = query_object["query"]
        query_used = query_text
        try:
            query_results = search_web(query_text)
        except WebSearchError as exc:
            logger.warning("Search failed for query '%s': %s", query_text, exc)
            self.search_errors.append({"query": query_text, "error": str(exc)})
            return []

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
                    self.search_errors.append({"query": fallback_query, "error": str(exc)})
                    query_results = []

        limited_results = query_results[: settings.SEARCH_MAX_RESULTS_PER_QUERY]
        self.last_raw_results_count += len(limited_results)

        collected_results: list[dict] = []
        for result in limited_results:
            url = result.get("url")
            source_domain = self._source_domain(url)
            query_family = self._text(query_object.get("query_family")) or "unknown"
            source_family = self._infer_source_family(
                result,
                source_domain,
                query_text,
                query_object,
            )
            collected_results.append(
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
                    "query_family": query_family,
                    "source_family": source_family,
                    "expansion_round": query_object.get("expansion_round", 0),
                    "source_domain": source_domain,
                    "source_type": self._infer_source_type(
                        result,
                        source_domain,
                        query_text,
                        source_family,
                    ),
                }
            )
        return collected_results

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
        best_by_key: dict[str, dict] = {}
        for result in results:
            candidate_key = self._candidate_key(result)
            current_result = best_by_key.get(candidate_key)
            if current_result is None or self._candidate_quality_key(
                result
            ) > self._candidate_quality_key(current_result):
                best_by_key[candidate_key] = result

        return list(best_by_key.values())

    def _candidate_key(self, result: dict) -> str:
        canonical_url = result.get("canonical_url") or result.get("url")
        if isinstance(canonical_url, str) and canonical_url.strip():
            return f"url:{self._normalize_candidate_url(canonical_url)}"

        title = " ".join(str(result.get("title") or "").casefold().split())
        domain = str(result.get("source_domain") or "").casefold()
        return f"title-domain:{title}:{domain}"

    def _candidate_quality_key(self, result: dict) -> tuple[int, int, int, int]:
        return (
            self._url_quality_score(result.get("url")),
            min(len(self._text(result.get("snippet"))), 500),
            self._query_family_specificity_score(result.get("query_family")),
            self._source_family_score(result.get("source_family")),
        )

    def _normalize_candidate_url(self, url: str) -> str:
        parsed_url = urlsplit(url.strip())
        filtered_query = [
            (key, value)
            for key, value in parse_qsl(parsed_url.query, keep_blank_values=True)
            if not key.casefold().startswith("utm_")
            and key.casefold()
            not in {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source"}
        ]
        cleaned_url = urlunsplit(
            (
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                urlencode(filtered_query, doseq=True),
                "",
            )
        )
        return normalize_url(cleaned_url)

    def _url_quality_score(self, url: object) -> int:
        useful_url = self._text(url)
        if not useful_url:
            return 0
        score = 1
        parsed_url = urlsplit(useful_url)
        if parsed_url.scheme == "https":
            score += 1
        if parsed_url.path and parsed_url.path != "/":
            score += 1
        if not parsed_url.query:
            score += 1
        return score

    def _query_family_specificity_score(self, value: object) -> int:
        family = self._text(value).casefold()
        scores = {
            "destination": 5,
            "field": 5,
            "academic_level": 4,
            "scholarship_type": 4,
            "nationality": 4,
            "university": 3,
            "government": 3,
            "embassy": 3,
            "foundation": 2,
            "company": 2,
            "professional_association": 2,
            "international_organization": 2,
            "verified_secondary_source": 1,
        }
        return scores.get(family, 0)

    def _source_family_score(self, value: object) -> int:
        family = self._text(value).casefold()
        scores = {
            "government": 7,
            "university": 7,
            "embassy": 6,
            "international_organization": 6,
            "foundation": 5,
            "professional_association": 5,
            "company": 4,
            "verified_secondary_source": 3,
            "unknown": 0,
        }
        return scores.get(family, 0)

    def _source_domain(self, url: object) -> str:
        if not isinstance(url, str) or not url.strip():
            return ""
        return urlsplit(url).netloc.lower().removeprefix("www.")

    def _infer_source_type(
        self,
        result: dict,
        source_domain: str,
        query_text: str,
        source_family: str = "",
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
        if "embassy" in haystack or source_family == "embassy":
            return "government"
        if source_family == "international_organization":
            return "organization"
        if source_family == "professional_association":
            return "organization"
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

    def _infer_source_family(
        self,
        result: dict,
        source_domain: str,
        query_text: str,
        query_object: dict,
    ) -> str:
        query_source_family = self._text(query_object.get("source_family")).casefold()
        if query_source_family and query_source_family != "unknown":
            return query_source_family

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
        if "embassy" in haystack or "consulate" in haystack:
            return "embassy"
        if "world bank" in haystack or "unesco" in haystack or "united nations" in haystack:
            return "international_organization"
        if "foundation" in haystack:
            return "foundation"
        if "company" in haystack or "corporate" in haystack or "technology" in haystack:
            return "company"
        if "association" in haystack or "society" in haystack:
            return "professional_association"
        if self._looks_like_verified_news(source_domain, haystack):
            return "verified_secondary_source"
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

    def _text(self, value: object) -> str:
        return " ".join(str(value or "").strip().split())
