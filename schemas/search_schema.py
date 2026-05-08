from __future__ import annotations

from config.settings import settings
from utils.url_utils import normalize_useful_url

MAX_GENERATED_QUERIES = settings.SEARCH_MAX_QUERIES
REQUIRED_QUERY_FIELDS = ("query", "target_country", "reason", "priority")
REQUIRED_RESULT_FIELDS = (
    "title",
    "url",
    "snippet",
    "source",
    "query",
    "query_used",
    "target_country",
    "priority",
)


class SearchQueryValidationError(ValueError):
    pass


class SearchResultValidationError(ValueError):
    pass


def validate_generated_queries(
    raw_queries: object,
    max_queries: int | None = None,
) -> list[dict]:
    if not isinstance(raw_queries, list):
        raise SearchQueryValidationError("Generated queries must be a list.")

    query_limit = max_queries or settings.SEARCH_MAX_QUERIES
    cleaned_queries: list[dict] = []
    seen_queries: set[str] = set()

    for raw_query in raw_queries:
        if not isinstance(raw_query, dict):
            continue

        query = _clean_text(raw_query.get("query"))
        target_country = _clean_text(raw_query.get("target_country"))
        reason = _clean_text(raw_query.get("reason"))
        priority = _clean_priority(raw_query.get("priority"))

        if not query:
            continue
        if not target_country:
            continue
        if not reason:
            continue
        if priority is None:
            continue

        query_key = query.casefold()
        if query_key in seen_queries:
            continue

        seen_queries.add(query_key)
        cleaned_queries.append(
            {
                "query": query,
                "target_country": target_country,
                "reason": reason,
                "priority": len(cleaned_queries) + 1,
            }
        )

        if len(cleaned_queries) == query_limit:
            break

    if not cleaned_queries:
        raise SearchQueryValidationError("No valid generated queries were returned.")

    return cleaned_queries


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    cleaned_value = " ".join(value.strip().split())
    return cleaned_value or None


def _clean_priority(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def validate_search_results(raw_results: object) -> list[dict]:
    if not isinstance(raw_results, list):
        raise SearchResultValidationError("Search results must be a list.")

    cleaned_results: list[dict] = []
    for raw_result in raw_results:
        if not isinstance(raw_result, dict):
            continue

        title = _clean_text(raw_result.get("title"))
        url = normalize_useful_url(raw_result.get("url"))
        snippet = _clean_text(raw_result.get("snippet"))
        source = _clean_text(raw_result.get("source"))
        query = _clean_text(raw_result.get("query"))
        query_used = _clean_text(raw_result.get("query_used")) or query
        target_country = _clean_text(raw_result.get("target_country"))
        priority = _clean_priority(raw_result.get("priority"))

        if not all((title, url, snippet, source, query, target_country)):
            continue
        if priority is None:
            continue

        cleaned_results.append(
            {
                "title": title,
                "url": url,
                "source_url": url,
                "original_url": normalize_useful_url(raw_result.get("original_url")) or url,
                "snippet": snippet,
                "source": source,
                "query": query,
                "query_used": query_used,
                "target_country": target_country,
                "priority": priority,
                **_optional_search_metadata(raw_result),
            }
        )

    return cleaned_results


def _optional_search_metadata(raw_result: dict) -> dict:
    metadata: dict[str, str] = {}
    for field in ("canonical_url", "source_domain", "source_type"):
        value = _clean_text(raw_result.get(field))
        if value:
            metadata[field] = value
    return metadata
