"""
api/main.py — FastAPI service for MultiAgentic-Scholarships.

Endpoints:
  GET  /           → API info
  GET  /health     → LLM backend status
  POST /search     → Full pipeline (profile text → ranked scholarships)
  POST /semantic-search → Semantic search over the SQLite knowledge base
  GET  /scholarships    → Paginated list of scholarships from the KB
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in path when running from api/ subdirectory
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config.settings import settings

app = FastAPI(
    title="MultiAgentic Scholarships API",
    description=(
        "Multi-agent AI scholarship discovery system — AMD Developer Hackathon 2026.\n\n"
        "LLM-powered semantic search replaces RAG/ChromaDB."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class SearchRequest(BaseModel):
    user_input: str
    max_results: int = 10


class SemanticSearchRequest(BaseModel):
    query: str
    limit: int = 50
    top_k: int = 10


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "MultiAgentic Scholarships API",
        "version": "1.0.0",
        "llm_provider": settings.LLM_PROVIDER,
        "semantic_search_enabled": settings.SEMANTIC_SEARCH_ENABLED,
        "docs": "/docs",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health")
def health():
    """Check LLM backend connectivity."""
    llm_status = "unknown"
    llm_error = None
    try:
        from llm.provider import generate_text
        response = generate_text("Reply with: OK")
        llm_status = "ok" if response else "empty_response"
    except Exception as exc:
        llm_status = "error"
        llm_error = str(exc)

    db_status = "unknown"
    try:
        from database.repository import list_recent_scholarships
        count = len(list_recent_scholarships(limit=1))
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {exc}"

    return {
        "status": "ok" if llm_status == "ok" else "degraded",
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.OLLAMA_MODEL if settings.LLM_PROVIDER == "ollama" else settings.REMOTE_LLM_MODEL,
        "llm_status": llm_status,
        "llm_error": llm_error,
        "database_status": db_status,
        "semantic_search_enabled": settings.SEMANTIC_SEARCH_ENABLED,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/semantic-search")
def semantic_search(req: SemanticSearchRequest):
    """
    Semantic search over the SQLite knowledge base using the LLM.
    No RAG / ChromaDB — the model ranks scholarships directly.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        from rag.vector_store import llm_semantic_rank, build_text_for_scholarship
        from database.repository import list_recent_scholarships
        import json

        raw = list_recent_scholarships(limit=req.limit)

        # Deserialize JSON list fields
        def parse_list(val):
            if isinstance(val, list):
                return val
            try:
                return json.loads(val or "[]")
            except Exception:
                return []

        scholarships = [
            {
                "scholarship_name": r.get("scholarship_name"),
                "institution": r.get("institution"),
                "country": r.get("country"),
                "academic_level": r.get("academic_level"),
                "fields": parse_list(r.get("fields_json")),
                "benefits": parse_list(r.get("benefits_json")),
                "eligible_nationalities": parse_list(r.get("eligible_nationalities_json")),
                "required_languages": parse_list(r.get("required_languages_json")),
                "requirements": parse_list(r.get("requirements_json")),
                "deadline": r.get("deadline"),
                "application_status": r.get("application_status"),
                "source_url": r.get("source_url"),
                "source_reliability_score": r.get("source_reliability_score"),
                "extraction_confidence": r.get("extraction_confidence"),
            }
            for r in raw
        ]

        ranked = llm_semantic_rank(
            profile_text=req.query,
            scholarships=scholarships,
            top_k=req.top_k,
        )

        results = []
        for item in ranked[: req.top_k]:
            idx = item["index"]
            s = scholarships[idx]
            results.append({
                **s,
                "semantic_score": item["semantic_score"],
                "relevance_reason": item["reason"],
            })

        return {
            "query": req.query,
            "total_scanned": len(scholarships),
            "results_returned": len(results),
            "semantic_search_enabled": settings.SEMANTIC_SEARCH_ENABLED,
            "results": results,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/scholarships")
def list_scholarships(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Paginated list of scholarships from the knowledge base."""
    try:
        from database.repository import list_recent_scholarships
        all_scholarships = list_recent_scholarships(limit=limit + offset)
        page = all_scholarships[offset: offset + limit]
        return {
            "total": len(all_scholarships),
            "limit": limit,
            "offset": offset,
            "scholarships": page,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
