"""
MultiAgentic-Becas — EvaluatorAgent
Calcula el score de compatibilidad entre el perfil del usuario y cada beca.
"""
import json
from loguru import logger
from langchain_core.messages import SystemMessage, HumanMessage

from agents.llm_factory import get_llm
from config.prompts import EVALUATOR_SYSTEM_PROMPT
from models.schemas import ScholarshipEvaluation, ScoreBreakdown, CompatibilityLevel
from models.state import AgentState


def evaluator_agent(state: AgentState) -> dict:
    """
    Nodo LangGraph: Evalúa la compatibilidad de cada beca con el perfil del usuario.

    Args:
        state: Estado actual (requiere user_profile y raw_scholarships)

    Returns:
        dict con lista de evaluations rankeadas
    """
    logger.info("⚖️  EvaluatorAgent: evaluando compatibilidad beca-perfil...")

    profile = state.get("user_profile")
    scholarships = state.get("raw_scholarships", [])

    if not profile:
        return {"error": "No hay perfil para evaluar.", "current_step": "error"}

    if not scholarships:
        return {
            "evaluations": [],
            "current_step": "write",
            "messages": [
                {
                    "role": "assistant",
                    "content": "⚠️ No se encontraron becas para evaluar.",
                }
            ],
        }

    llm = get_llm(temperature=0.0)
    evaluations: list[ScholarshipEvaluation] = []

    profile_json = profile.model_dump_json(indent=2)

    for i, scholarship in enumerate(scholarships):
        logger.info(f"  Evaluando [{i+1}/{len(scholarships)}]: {scholarship.name[:60]}...")

        messages = [
            SystemMessage(content=EVALUATOR_SYSTEM_PROMPT),
            HumanMessage(
                content=f"""
Evaluate the compatibility between this student profile and scholarship:

STUDENT PROFILE:
{profile_json}

SCHOLARSHIP:
{scholarship.model_dump_json(indent=2)}

Return ONLY valid JSON with score (0-100), breakdown, recommendation, key_strengths, key_gaps, and notes.
                """
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

            eval_data = json.loads(raw_json)

            evaluation = ScholarshipEvaluation(
                scholarship=scholarship,
                score=eval_data["score"],
                breakdown=ScoreBreakdown(**eval_data["breakdown"]),
                recommendation=CompatibilityLevel(eval_data["recommendation"]),
                key_strengths=eval_data.get("key_strengths", []),
                key_gaps=eval_data.get("key_gaps", []),
                notes=eval_data.get("notes", ""),
            )
            evaluations.append(evaluation)

        except Exception as e:
            logger.warning(f"    ⚠️ Error evaluando '{scholarship.name[:40]}': {e}")
            continue

    # Rankear por score descendente
    evaluations.sort(key=lambda x: x.score, reverse=True)

    high_count = sum(1 for e in evaluations if e.recommendation == CompatibilityLevel.HIGH)
    logger.success(
        f"✅ EvaluatorAgent: {len(evaluations)} evaluaciones completadas | "
        f"{high_count} con compatibilidad ALTA"
    )

    return {
        "evaluations": evaluations,
        "current_step": "write",
        "messages": [
            {
                "role": "assistant",
                "content": (
                    f"⚖️ Evaluación completada.\n"
                    f"- Becas evaluadas: **{len(evaluations)}**\n"
                    f"- Alta compatibilidad: **{high_count}**\n\n"
                    f"Generando tu reporte personalizado..."
                ),
            }
        ],
    }
