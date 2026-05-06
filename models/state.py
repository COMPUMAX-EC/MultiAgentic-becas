"""
MultiAgentic-Becas — AgentState para LangGraph
Define el estado compartido entre todos los agentes del grafo.
"""
from __future__ import annotations
from typing import Annotated, Optional
from typing_extensions import TypedDict
import operator

from models.schemas import (
    UserProfile,
    Scholarship,
    ScholarshipEvaluation,
    BecasReport,
)


class AgentState(TypedDict):
    """
    Estado compartido del grafo LangGraph.

    Todos los agentes leen y escriben en este estado.
    LangGraph gestiona la immutabilidad y el paso entre nodos.
    """
    # ---- Input del usuario ----
    user_input: str                         # Texto libre del usuario

    # ---- Perfil estructurado ----
    user_profile: Optional[UserProfile]     # Generado por ProfilerAgent

    # ---- Búsqueda ----
    search_queries: list[str]               # Queries generadas para la web
    raw_scholarships: Annotated[            # Acumulación de becas encontradas
        list[Scholarship],
        operator.add                        # LangGraph merge: suma listas
    ]

    # ---- Evaluación ----
    evaluations: list[ScholarshipEvaluation]  # Generado por EvaluatorAgent

    # ---- Reporte final ----
    report: Optional[BecasReport]           # Generado por WriterAgent

    # ---- Control de flujo ----
    current_step: str                       # Nodo activo ("profiler", "search", etc.)
    error: Optional[str]                    # Mensaje de error si algo falla
    messages: Annotated[                    # Historial de mensajes para UI
        list[dict],
        operator.add
    ]
