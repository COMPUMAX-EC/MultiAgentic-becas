"""
MultiAgentic-Becas — SearchAgent
Genera queries de búsqueda y busca becas relevantes en la web.
"""
import json
from loguru import logger
from langchain_core.messages import SystemMessage, HumanMessage

from agents.llm_factory import get_llm
from config.prompts import SEARCH_SYSTEM_PROMPT
from config.settings import settings
from models.schemas import Scholarship
from models.state import AgentState
from tools.web_search import search_scholarships


def search_agent(state: AgentState) -> dict:
    """
    Nodo LangGraph: Busca becas relevantes basándose en el perfil del usuario.

    Args:
        state: Estado actual (requiere user_profile)

    Returns:
        dict con raw_scholarships y queries generadas
    """
    logger.info("🔍 SearchAgent: buscando becas relevantes...")

    profile = state.get("user_profile")
    if not profile:
        return {
            "error": "No hay perfil de usuario para buscar becas.",
            "current_step": "error",
        }

    llm = get_llm(temperature=0.3)

    # 1. Generar queries de búsqueda optimizadas
    profile_summary = f"""
    - Academic level: {profile.academic_level}
    - Field: {profile.field_of_study}
    - Country of origin: {profile.country_of_origin}
    - Target countries: {', '.join(profile.target_countries) or 'any'}
    - Languages: {', '.join(f"{l.language} ({l.proficiency})" for l in profile.languages)}
    - Financial need: {profile.financial_need}
    - Career goals: {profile.career_goals or 'not specified'}
    """

    messages = [
        SystemMessage(content=SEARCH_SYSTEM_PROMPT),
        HumanMessage(
            content=f"Generate search queries for this student profile:\n{profile_summary}"
        ),
    ]

    try:
        response = llm.invoke(messages)
        raw_json = response.content.strip()

        if raw_json.startswith("```"):
            raw_json = raw_json.split("```")[1]
            if raw_json.startswith("json"):
                raw_json = raw_json[4:]
            raw_json = raw_json.strip()

        queries: list[str] = json.loads(raw_json)
        logger.info(f"🔎 Queries generadas: {queries}")

    except Exception as e:
        logger.warning(f"Error generando queries LLM, usando fallback: {e}")
        queries = [
            f"scholarships {profile.academic_level} {profile.field_of_study} students from {profile.country_of_origin}",
            f"international scholarships {profile.field_of_study} Latin America 2025 2026",
            f"fully funded scholarships {profile.country_of_origin} {profile.academic_level}",
        ]

    # 2. Ejecutar búsquedas
    all_scholarships: list[Scholarship] = []
    for query in queries[: settings.max_search_results]:
        found = search_scholarships(query, max_results=settings.max_scholarships_per_search)
        all_scholarships.extend(found)
        logger.info(f"  ✓ Query '{query[:50]}...' → {len(found)} becas")

    # Eliminar duplicados por URL
    seen_urls = set()
    unique_scholarships = []
    for s in all_scholarships:
        if s.url not in seen_urls:
            seen_urls.add(s.url)
            unique_scholarships.append(s)

    logger.success(f"✅ SearchAgent: {len(unique_scholarships)} becas únicas encontradas")

    return {
        "search_queries": queries,
        "raw_scholarships": unique_scholarships,
        "current_step": "evaluate",
        "messages": [
            {
                "role": "assistant",
                "content": (
                    f"🔍 Búsqueda completada.\n"
                    f"- Queries ejecutadas: **{len(queries)}**\n"
                    f"- Becas encontradas: **{len(unique_scholarships)}**\n\n"
                    f"Evaluando compatibilidad con tu perfil..."
                ),
            }
        ],
    }
