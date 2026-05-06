"""
MultiAgentic-Becas — FastAPI Backend
Expone el pipeline de búsqueda de becas como REST API.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

from agents.orchestrator import run_scholarship_search
from config.settings import settings

app = FastAPI(
    title="MultiAgentic-Becas API",
    description="Sistema multi-agente para búsqueda inteligente de becas académicas",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request / Response models ────────────────────────────────────────────────

class SearchRequest(BaseModel):
    user_input: str
    """Descripción del estudiante y sus objetivos en texto libre."""


class SearchResponse(BaseModel):
    success: bool
    scholarships_found: int
    top_score: int | None
    summary: str
    top_recommendations: list[str]
    next_steps: list[str]
    has_motivation_letter: bool
    messages: list[dict]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "llm_backend": settings.llm_backend,
        "llm_model": (
            settings.vllm_model
            if settings.llm_backend == "amd_cloud"
            else settings.ollama_model
        ),
    }


@app.post("/search", response_model=SearchResponse)
def search_scholarships_endpoint(request: SearchRequest):
    """
    Ejecuta el pipeline multi-agente completo de búsqueda de becas.

    Acepta texto libre describiendo el perfil del estudiante y retorna
    becas rankeadas con evaluación de compatibilidad.
    """
    if not request.user_input.strip():
        raise HTTPException(status_code=400, detail="user_input no puede estar vacío")

    logger.info(f"POST /search — input: '{request.user_input[:60]}...'")

    try:
        final_state = run_scholarship_search(request.user_input)

        if final_state.get("error"):
            raise HTTPException(
                status_code=500,
                detail=final_state["error"]
            )

        report = final_state.get("report")
        evaluations = final_state.get("evaluations", [])

        return SearchResponse(
            success=True,
            scholarships_found=len(evaluations),
            top_score=evaluations[0].score if evaluations else None,
            summary=report.summary if report else "Sin resultados",
            top_recommendations=report.top_recommendations if report else [],
            next_steps=report.next_steps if report else [],
            has_motivation_letter=bool(report and report.motivation_letter_draft),
            messages=final_state.get("messages", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en /search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def root():
    return {
        "message": "MultiAgentic-Becas API v1.0",
        "docs": "/docs",
        "health": "/health",
    }
