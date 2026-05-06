from __future__ import annotations


ALLOWED_PAGE_STATUSES = {
    "read_success",
    "read_failed",
    "skipped_rejected_source",
    "skipped_empty_content",
    "cache_hit",
}


class PageSchemaError(ValueError):
    pass


def build_page_result(
    source: dict,
    status: str,
    raw_text_length: int = 0,
    cleaned_text: str = "",
    error: str | None = None,
    cache_path: str | None = None,
) -> dict:
    if status not in ALLOWED_PAGE_STATUSES:
        raise PageSchemaError(f"Unsupported page status: {status}")

    return {
        "url": source.get("url", ""),
        "title": source.get("title", ""),
        "source_type": source.get("source_type", ""),
        "source_decision": source.get("decision", ""),
        "status": status,
        "raw_text_length": raw_text_length,
        "cleaned_text_length": len(cleaned_text),
        "cleaned_text": cleaned_text,
        "error": error,
        "cache_path": cache_path,
    }
