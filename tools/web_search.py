"""
tools/web_search.py — DuckDuckGo web search returning raw result dicts.

Provides:
    search_web(query, max_results) -> list[dict]
    WebSearchError                 -> raised on unrecoverable search failures

Each result dict has the keys expected by SearchAgent:
    url, canonical_url, title, snippet, source
"""
from __future__ import annotations

import time

from loguru import logger


class WebSearchError(RuntimeError):
    """Raised when the web search cannot be completed."""


def search_web(query: str, max_results: int | None = None) -> list[dict]:
    """
    Search the web using DuckDuckGo and return raw result dicts.

    Args:
        query:       Search query string.
        max_results: Maximum number of results to return.
                     Defaults to settings.SEARCH_MAX_RESULTS_PER_QUERY if available.

    Returns:
        List of dicts with keys: url, canonical_url, title, snippet, source.

    Raises:
        WebSearchError: If DuckDuckGo is unreachable or returns an error.
    """
    if max_results is None:
        try:
            from config.settings import settings
            max_results = settings.SEARCH_MAX_RESULTS_PER_QUERY
        except Exception:
            max_results = 10

    try:
        from duckduckgo_search import DDGS
    except ImportError as exc:
        raise WebSearchError(
            "duckduckgo-search is not installed. Run: uv add duckduckgo-search"
        ) from exc

    raw_results: list[dict] = []
    last_exc: Exception | None = None

    for attempt in range(1, 4):   # up to 3 attempts with back-off
        try:
            with DDGS() as ddgs:
                raw_results = list(
                    ddgs.text(
                        query,
                        max_results=max_results,
                        region="wt-wt",
                        safesearch="moderate",
                    )
                )
            break   # success
        except Exception as exc:
            last_exc = exc
            logger.debug(
                "DuckDuckGo attempt %d/%d failed for query '%s': %s",
                attempt, 3, query[:60], exc,
            )
            if attempt < 3:
                time.sleep(attempt * 1.5)

    if raw_results is None and last_exc is not None:
        raise WebSearchError(
            f"DuckDuckGo search failed after 3 attempts: {last_exc}"
        ) from last_exc

    results: list[dict] = []
    for r in raw_results or []:
        url = r.get("href") or r.get("url") or ""
        if not url:
            continue
        results.append({
            "url":           url,
            "canonical_url": url,
            "title":         r.get("title", ""),
            "snippet":       r.get("body", ""),
            "source":        _extract_domain(url),
        })

    logger.debug("search_web('%s') → %d results", query[:60], len(results))
    return results


def _extract_domain(url: str) -> str:
    """Return the bare domain from a URL string."""
    try:
        from urllib.parse import urlsplit
        return urlsplit(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""
