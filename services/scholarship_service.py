from __future__ import annotations

from collections import Counter

from config.settings import settings
from database.repository import (
    init_database,
    save_extraction_run,
    save_profile,
    save_scholarships,
    save_search_queries,
    save_sources,
)


def save_to_knowledge_base(
    normalized_profile: dict,
    queries: list[dict],
    validated_sources: list[dict],
    extracted_scholarships: list[dict],
    extraction_errors: list[dict] | None = None,
) -> dict:
    summary = {
        "profiles_saved": 0,
        "queries_saved": 0,
        "sources_saved": 0,
        "scholarships_inserted": 0,
        "scholarships_updated": 0,
        "errors": [],
    }

    if not settings.KNOWLEDGE_BASE_ENABLED:
        summary["errors"].append("Knowledge base is disabled.")
        return summary

    try:
        init_database()
        profile_id = save_profile(normalized_profile)
        summary["profiles_saved"] = 1 if profile_id else 0
        summary["queries_saved"] = save_search_queries(profile_id, queries)
        summary["sources_saved"] = save_sources(validated_sources)
        scholarship_summary = save_scholarships(extracted_scholarships)
        summary["scholarships_inserted"] = scholarship_summary["inserted"]
        summary["scholarships_updated"] = scholarship_summary["updated"]

        counts_by_source = Counter(
            scholarship.get("source_url") for scholarship in extracted_scholarships
        )
        saved_error_urls = set()
        for source_url, scholarships_found in counts_by_source.items():
            save_extraction_run(
                profile_id,
                source_url,
                "success",
                scholarships_found,
            )

        for extraction_error in extraction_errors or []:
            source_url = extraction_error.get("url")
            saved_error_urls.add(source_url)
            save_extraction_run(
                profile_id,
                source_url,
                "error",
                0,
                extraction_error.get("error"),
            )

        for source in validated_sources:
            source_url = source.get("url")
            if source_url in counts_by_source or source_url in saved_error_urls:
                continue
            save_extraction_run(profile_id, source_url, "no_scholarships", 0)
    except Exception as exc:
        summary["errors"].append(str(exc))

    return summary
