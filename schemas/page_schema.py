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
        "source_url": source.get("source_url") or source.get("url", ""),
        "original_url": source.get("original_url") or source.get("url", ""),
        "title": source.get("title", ""),
        "page_title": source.get("title", ""),
        "source_type": source.get("source_type", ""),
        "source_decision": source.get("decision", ""),
        "source_acceptance_status": source.get("acceptance_status", ""),
        "validation_status": source.get("validation_status")
        or source.get("acceptance_status", ""),
        "validation_reason": source.get("validation_reason", ""),
        "warnings": list(source.get("warnings") or []),
        "query_used": source.get("query_used", ""),
        "query_family": source.get("query_family", ""),
        "source_family": source.get("source_family", ""),
        "status": status,
        "read_status": status,
        "raw_text_length": raw_text_length,
        "cleaned_text_length": len(cleaned_text),
        "cleaned_text": cleaned_text,
        "error": error,
        "read_error": error,
        "cache_path": cache_path,
    }
