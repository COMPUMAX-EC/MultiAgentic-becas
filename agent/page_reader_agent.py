from __future__ import annotations

from config.settings import settings
from schemas.page_schema import build_page_result
from services.cache_service import PageCacheService
from tools.page_reader import PageReadError, read_page
from tools.text_cleaner import clean_text


class PageReaderAgent:
    def __init__(self, cache_service: PageCacheService | None = None) -> None:
        self.cache_service = cache_service or PageCacheService()

    def read_pages(self, validated_sources: list[dict]) -> list[dict]:
        return [self.read_page_source(source) for source in validated_sources]

    def read_page_source(self, source: dict) -> dict:
        decision = source.get("decision")
        validation_status = source.get("validation_status") or source.get(
            "acceptance_status"
        )
        url = str(source.get("url") or "").strip()

        if decision not in settings.PAGE_ALLOWED_DECISIONS and validation_status not in {
            "accepted",
            "accepted_with_warning",
        }:
            return build_page_result(
                source,
                "skipped_rejected_source",
                error=f"Source decision '{decision}' is not allowed for page reading.",
            )

        if settings.PAGE_CACHE_ENABLED:
            cached_text, cache_path = self.cache_service.load(url)
            if cached_text is not None:
                return build_page_result(
                    source,
                    "cache_hit",
                    raw_text_length=len(cached_text),
                    cleaned_text=cached_text,
                    cache_path=str(cache_path),
                )

        try:
            raw_content = read_page(url)
        except PageReadError as exc:
            return build_page_result(source, "read_failed", error=str(exc))

        cleaned_text = clean_text(raw_content)
        if not cleaned_text:
            return build_page_result(
                source,
                "skipped_empty_content",
                raw_text_length=len(raw_content),
                error="Page content was empty after cleaning.",
            )

        cache_path = None
        if settings.PAGE_CACHE_ENABLED:
            cache_path = self.cache_service.save(url, cleaned_text)

        return build_page_result(
            source,
            "read_success",
            raw_text_length=len(raw_content),
            cleaned_text=cleaned_text,
            cache_path=str(cache_path) if cache_path else None,
        )
