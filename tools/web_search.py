from __future__ import annotations

import socket
import subprocess
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote_plus, urlparse
import urllib.error
import urllib.request

from config.settings import settings


class WebSearchError(RuntimeError):
    pass


class DuckDuckGoHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict] = []
        self._in_result = False
        self._result_div_depth = 0
        self._capture_title = False
        self._capture_snippet = False
        self._current_result: dict = {}
        self._title_parts: list[str] = []
        self._snippet_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        class_name = attributes.get("class", "")

        if tag == "div" and "result results_links" in class_name:
            self._in_result = True
            self._result_div_depth = 1
            self._current_result = {}
            self._title_parts = []
            self._snippet_parts = []
            return

        if not self._in_result:
            return

        if tag == "div":
            self._result_div_depth += 1

        if tag == "a" and attributes.get("class") == "result__a":
            self._capture_title = True
            href = attributes.get("href")
            if href:
                self._current_result["url"] = _extract_duckduckgo_target_url(href)
            return

        if tag == "a" and attributes.get("class") == "result__snippet":
            self._capture_snippet = True

    def handle_endtag(self, tag: str) -> None:
        if not self._in_result:
            return

        if tag == "a":
            self._capture_title = False
            self._capture_snippet = False
            return

        if tag == "div":
            self._result_div_depth -= 1
            if self._result_div_depth > 0:
                return

            if self._current_result:
                title = _clean_text("".join(self._title_parts))
                snippet = _clean_text("".join(self._snippet_parts))
                url = _clean_text(self._current_result.get("url", ""))

                if title and snippet and url:
                    self.results.append(
                        {
                            "title": title,
                            "url": url,
                            "snippet": snippet,
                        }
                    )

            self._in_result = False
            self._result_div_depth = 0
            self._current_result = {}
            self._title_parts = []
            self._snippet_parts = []

    def handle_data(self, data: str) -> None:
        if self._capture_title:
            self._title_parts.append(data)
        elif self._capture_snippet:
            self._snippet_parts.append(data)


def search_web(query: str) -> list[dict]:
    if not query or not query.strip():
        raise WebSearchError("Search query cannot be empty.")

    provider = settings.SEARCH_PROVIDER.strip().lower()
    if provider != "duckduckgo":
        raise WebSearchError(f"Unsupported search provider: {settings.SEARCH_PROVIDER}")

    search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    request = urllib.request.Request(
        url=search_url,
        headers={"User-Agent": "Mozilla/5.0"},
        method="GET",
    )

    try:
        html_content = _fetch_html_with_urllib(request)
    except socket.timeout as exc:
        raise WebSearchError(
            f"Search request timed out after {settings.SEARCH_TIMEOUT_SECONDS} seconds."
        ) from exc
    except urllib.error.URLError as exc:
        raise WebSearchError(
            f"Search request failed for provider '{settings.SEARCH_PROVIDER}'."
        ) from exc

    parser = DuckDuckGoHTMLParser()
    parser.feed(html_content)
    if not parser.results:
        html_content = _fetch_html_with_powershell(search_url)
        parser = DuckDuckGoHTMLParser()
        parser.feed(html_content)

    results: list[dict] = []
    for result in parser.results[: settings.SEARCH_MAX_RESULTS_PER_QUERY]:
        results.append(
            {
                "title": result["title"],
                "url": result["url"],
                "snippet": result["snippet"],
                "source": settings.SEARCH_PROVIDER,
                "query": query.strip(),
            }
        )

    return results


def _extract_duckduckgo_target_url(raw_url: str) -> str:
    if raw_url.startswith("//"):
        raw_url = f"https:{raw_url}"

    parsed_url = urlparse(raw_url)
    query_parameters = parse_qs(parsed_url.query)
    target_url = query_parameters.get("uddg", [raw_url])[0]
    return unescape(target_url)


def _clean_text(value: str) -> str:
    return " ".join(unescape(value).split())


def _fetch_html_with_urllib(request: urllib.request.Request) -> str:
    with urllib.request.urlopen(
        request, timeout=settings.SEARCH_TIMEOUT_SECONDS
    ) as response:
        return response.read().decode("utf-8", errors="ignore")


def _fetch_html_with_powershell(search_url: str) -> str:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
            f"(Invoke-WebRequest -UseBasicParsing '{search_url}').Content"
        ),
    ]

    try:
        completed_process = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=settings.SEARCH_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise WebSearchError(
            f"Search request timed out after {settings.SEARCH_TIMEOUT_SECONDS} seconds."
        ) from exc
    except (OSError, subprocess.CalledProcessError) as exc:
        raise WebSearchError("Fallback search request failed.") from exc

    return completed_process.stdout or ""
