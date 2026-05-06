from __future__ import annotations

from config.settings import settings
from rag.retriever import ScholarshipRetriever


def run_retrieval(normalized_profile: dict) -> dict:
    summary = {
        "retrieval_enabled": settings.RETRIEVAL_ENABLED,
        "retrieved_count": 0,
        "usable_results": 0,
        "skipped_closed_or_expired": 0,
        "errors": [],
    }

    if not settings.RETRIEVAL_ENABLED:
        return {
            "summary": summary,
            "retrieval_results": [],
        }

    retriever = ScholarshipRetriever()
    try:
        retrieval_results = retriever.retrieve(normalized_profile)
        summary["retrieved_count"] = len(retrieval_results)
        summary["usable_results"] = len(retrieval_results)
        summary["skipped_closed_or_expired"] = retriever.skipped_closed_or_expired
        return {
            "summary": summary,
            "retrieval_results": retrieval_results,
        }
    except Exception as exc:
        summary["errors"].append(str(exc))
        return {
            "summary": summary,
            "retrieval_results": [],
        }
