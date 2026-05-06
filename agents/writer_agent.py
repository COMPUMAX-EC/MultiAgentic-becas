"""
MultiAgentic-Becas — WriterAgent
Genera el reporte final y (opcionalmente) una carta de motivación.
"""
from loguru import logger
from langchain_core.messages import SystemMessage, HumanMessage

from agents.llm_factory import get_llm
from config.prompts import WRITER_SYSTEM_PROMPT
from models.schemas import BecasReport, CompatibilityLevel
from models.state import AgentState


def writer_agent(state: AgentState) -> dict:
    """
    Nodo LangGraph: Genera el reporte final en español con recomendaciones claras.

    Args:
        state: Estado actual (requiere user_profile y evaluations)

    Returns:
        dict con el BecasReport completo
    """
    logger.info("✍️  WriterAgent: generando reporte final...")

    profile = state.get("user_profile")
    evaluations = state.get("evaluations", [])

    if not profile:
        return {"error": "No hay perfil para generar el reporte.", "current_step": "error"}

    if not evaluations:
        # Reporte vacío
        report = BecasReport(
            user_profile=profile,
            evaluations=[],
            summary="No se encontraron becas que coincidan con tu perfil en esta búsqueda.",
            top_recommendations=["Amplía los países de destino", "Considera niveles académicos adyacentes"],
            next_steps=["Actualiza tu perfil con más detalles", "Intenta nuevamente con otras palabras clave"],
        )
        return {
            "report": report,
            "current_step": "done",
            "messages": [{"role": "assistant", "content": "ℹ️ No se encontraron becas compatibles esta vez."}],
        }

    llm = get_llm(temperature=0.4)

    # Preparar resumen de las top 5 becas para el prompt
    top_5 = evaluations[:5]
    scholarships_summary = "\n\n".join([
        f"[{i+1}] {e.scholarship.name} | Score: {e.score}/100 | {e.recommendation}\n"
        f"  Provider: {e.scholarship.provider}\n"
        f"  Deadline: {e.scholarship.deadline or 'No especificado'}\n"
        f"  Fortalezas: {', '.join(e.key_strengths[:2])}\n"
        f"  Brechas: {', '.join(e.key_gaps[:2])}"
        for i, e in enumerate(top_5)
    ])

    messages = [
        SystemMessage(content=WRITER_SYSTEM_PROMPT),
        HumanMessage(
            content=f"""
Genera un reporte completo de becas EN ESPAÑOL para este estudiante.

PERFIL DEL ESTUDIANTE:
- Nombre: {profile.name or 'Estudiante'}
- Nivel: {profile.academic_level}
- Campo: {profile.field_of_study}
- País origen: {profile.country_of_origin}
- Destinos preferidos: {', '.join(profile.target_countries) or 'Cualquier país'}

TOP BECAS ENCONTRADAS (rankeadas por compatibilidad):
{scholarships_summary}

Por favor genera:
1. Un resumen ejecutivo (2-3 párrafos)
2. Top 3 recomendaciones específicas con justificación
3. Lista de próximos pasos concretos (mínimo 5 acciones)

Sé específico, práctico y motivador. Menciona fechas y requisitos clave.
            """
        ),
    ]

    try:
        response = llm.invoke(messages)
        report_text = response.content.strip()

        # Parsear secciones del reporte
        sections = _parse_report_sections(report_text)

        # Generar carta de motivación para la beca #1 si es de alta compatibilidad
        motivation_letter = None
        if top_5 and top_5[0].recommendation == CompatibilityLevel.HIGH:
            motivation_letter = _generate_motivation_letter(
                llm, profile, top_5[0].scholarship
            )

        report = BecasReport(
            user_profile=profile,
            evaluations=evaluations,
            summary=sections.get("summary", report_text[:500]),
            top_recommendations=sections.get("recommendations", [
                f"{e.scholarship.name} (Score: {e.score}/100)" for e in top_5[:3]
            ]),
            next_steps=sections.get("next_steps", ["Visita las páginas oficiales de cada beca"]),
            motivation_letter_draft=motivation_letter,
        )

        logger.success("✅ WriterAgent: reporte generado exitosamente")

        return {
            "report": report,
            "current_step": "done",
            "messages": [
                {
                    "role": "assistant",
                    "content": (
                        "✅ ¡Tu reporte está listo!\n\n"
                        f"Encontré **{len(evaluations)} becas** evaluadas para tu perfil.\n"
                        f"Las mejores oportunidades son:\n"
                        + "\n".join(
                            f"  {i+1}. **{e.scholarship.name}** — Score: {e.score}/100"
                            for i, e in enumerate(top_5[:3])
                        )
                    ),
                }
            ],
        }

    except Exception as e:
        logger.error(f"❌ Error generando reporte: {e}")
        return {
            "error": f"Error generando reporte: {e}",
            "current_step": "error",
        }


def _parse_report_sections(text: str) -> dict:
    """Extrae secciones del texto del reporte generado por el LLM."""
    result = {"summary": "", "recommendations": [], "next_steps": []}

    lines = text.split("\n")
    current_section = "summary"
    buffer = []

    for line in lines:
        line_lower = line.lower().strip()
        if any(k in line_lower for k in ["recomendaci", "top 3", "mejores becas"]):
            result["summary"] = "\n".join(buffer).strip()
            buffer = []
            current_section = "recommendations"
        elif any(k in line_lower for k in ["próximos pasos", "siguiente", "acciones"]):
            if current_section == "recommendations":
                result["recommendations"] = [
                    l.strip().lstrip("123.-• ") for l in buffer if l.strip()
                ]
            buffer = []
            current_section = "next_steps"
        else:
            buffer.append(line)

    # Guardar último buffer
    if current_section == "next_steps" and buffer:
        result["next_steps"] = [
            l.strip().lstrip("123.-• ") for l in buffer if l.strip()
        ]
    elif not result["summary"]:
        result["summary"] = text[:800]

    return result


def _generate_motivation_letter(llm, profile, scholarship) -> str:
    """Genera un borrador de carta de motivación para la beca principal."""
    logger.info(f"  ✍️ Generando carta de motivación para: {scholarship.name[:50]}...")

    messages = [
        SystemMessage(content=WRITER_SYSTEM_PROMPT),
        HumanMessage(
            content=f"""
Escribe un borrador de carta de motivación EN ESPAÑOL para la siguiente beca.

BECA: {scholarship.name}
ORGANIZACIÓN: {scholarship.provider}
DESCRIPCIÓN: {scholarship.description[:400]}

PERFIL DEL ESTUDIANTE:
- Nivel académico: {profile.academic_level}
- Campo de estudio: {profile.field_of_study}
- País de origen: {profile.country_of_origin}
- Objetivos: {profile.career_goals or 'Desarrollo profesional en ' + profile.field_of_study}
- Idiomas: {', '.join(f"{l.language}" for l in profile.languages)}

La carta debe:
- Tener máximo 450 palabras
- Conectar genuinamente los objetivos del estudiante con la misión de la beca
- Mencionar logros específicos del campo de estudio
- Tener un tono profesional pero auténtico
- Incluir placeholders claros como [TU NOMBRE], [TU INSTITUCIÓN ACTUAL], [TU LOGRO ESPECÍFICO]
            """
        ),
    ]

    try:
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception as e:
        logger.warning(f"  ⚠️ No se pudo generar la carta: {e}")
        return None
