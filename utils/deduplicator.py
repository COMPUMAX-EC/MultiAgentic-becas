from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str) -> str:
    split_url = urlsplit(url.strip())
    normalized_path = split_url.path.rstrip("/")
    if not normalized_path and split_url.path.startswith("/"):
        normalized_path = "/"

    return urlunsplit(
        (
            split_url.scheme.lower(),
            split_url.netloc.lower(),
            normalized_path,
            split_url.query,
            "",
        )
    )


def deduplicate_by_url(results: list[dict]) -> list[dict]:
    deduplicated_results: list[dict] = []
    seen_urls: set[str] = set()

    for result in results:
        url = result.get("url")
        if not isinstance(url, str) or not url.strip():
            continue

        normalized_result_url = normalize_url(url)
        if normalized_result_url in seen_urls:
            continue

        seen_urls.add(normalized_result_url)
        deduplicated_results.append(result)

    return deduplicated_results
