from __future__ import annotations

from config.settings import settings
from schemas.search_schema import validate_search_results
from tools.web_search import WebSearchError, search_web
from utils.deduplicator import deduplicate_by_url
from utils.logger import get_logger


logger = get_logger(__name__)


class SearchAgent:
    def search(self, generated_queries: list[dict]) -> list[dict]:
        aggregated_results: list[dict] = []

        for query_object in generated_queries:
            query_text = query_object["query"]
            try:
                query_results = search_web(query_text)
            except WebSearchError as exc:
                logger.warning("Search failed for query '%s': %s", query_text, exc)
                continue

            if not query_results:
                fallback_query = self._build_fallback_query(query_text)
                if fallback_query and fallback_query != query_text:
                    logger.info(
                        "Retrying query with simplified search text: %s", fallback_query
                    )
                    try:
                        query_results = search_web(fallback_query)
                    except WebSearchError as exc:
                        logger.warning(
                            "Fallback search failed for query '%s': %s",
                            fallback_query,
                            exc,
                        )
                        query_results = []

            limited_results = query_results[: settings.SEARCH_MAX_RESULTS_PER_QUERY]
            for result in limited_results:
                aggregated_results.append(
                    {
                        "title": result.get("title"),
                        "url": result.get("url"),
                        "snippet": result.get("snippet"),
                        "source": result.get("source"),
                        "query": query_text,
                        "target_country": query_object.get("target_country"),
                        "priority": query_object.get("priority"),
                    }
                )

        return deduplicate_by_url(validate_search_results(aggregated_results))

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
