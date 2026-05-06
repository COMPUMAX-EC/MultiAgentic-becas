"""
MultiAgentic-Becas — ProfilerAgent
Toma el texto libre del usuario y extrae un UserProfile estructurado.
"""
import json
from loguru import logger
from langchain_core.messages import SystemMessage, HumanMessage

from agents.llm_factory import get_llm
from config.prompts import PROFILER_SYSTEM_PROMPT
from models.schemas import UserProfile
from models.state import AgentState


def profiler_agent(state: AgentState) -> dict:
    """
    Nodo LangGraph: Analiza el input del usuario y genera un UserProfile.

    Args:
        state: Estado actual del grafo

    Returns:
        dict con claves a actualizar en el estado
    """
    logger.info("🎓 ProfilerAgent: analizando perfil del estudiante...")

    llm = get_llm(temperature=0.0)  # Determinista para extracción estructurada

    messages = [
        SystemMessage(content=PROFILER_SYSTEM_PROMPT),
        HumanMessage(content=f"""
Extrae el perfil del estudiante del siguiente texto:

---
{state["user_input"]}
---

Devuelve SOLO el JSON válido del perfil. Si algún campo no está en el texto, usa valores por defecto razonables.
El campo 'academic_level' debe ser uno de: undergraduate, master, phd, postdoc, other.
El campo 'country_of_origin' debe ser el país en inglés (ej: Colombia, not "colombiano").
        """),
    ]

    try:
        response = llm.invoke(messages)
        raw_json = response.content.strip()

        # Limpiar posibles bloques de código Markdown
        if raw_json.startswith("```"):
            raw_json = raw_json.split("```")[1]
            if raw_json.startswith("json"):
                raw_json = raw_json[4:]
            raw_json = raw_json.strip()

        profile_data = json.loads(raw_json)
        profile = UserProfile(**profile_data)

        logger.success(
            f"✅ Perfil extraído: {profile.name or 'Anónimo'} | "
            f"{profile.academic_level} | {profile.field_of_study} | "
            f"Origen: {profile.country_of_origin}"
        )

        return {
            "user_profile": profile,
            "current_step": "search",
            "messages": [
                {
                    "role": "assistant",
                    "content": (
                        f"✅ Perfil analizado correctamente.\n"
                        f"- Nivel: **{profile.academic_level}**\n"
                        f"- Área: **{profile.field_of_study}**\n"
                        f"- País origen: **{profile.country_of_origin}**\n"
                        f"- Destinos: {', '.join(profile.target_countries) or 'Cualquier país'}"
                    ),
                }
            ],
        }

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"❌ Error parseando perfil: {e}")
        return {
            "error": f"No pude extraer el perfil correctamente: {e}",
            "current_step": "error",
            "messages": [
                {
                    "role": "assistant",
                    "content": "❌ Hubo un problema analizando tu perfil. Por favor proporciona más detalles.",
                }
            ],
        }
