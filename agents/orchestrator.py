"""
MultiAgentic-Becas — Orchestrator (LangGraph StateGraph)
Define el grafo de agentes y el flujo de ejecución.
"""
from loguru import logger
from langgraph.graph import StateGraph, END

from models.state import AgentState
from agents.profiler_agent import profiler_agent
from agents.search_agent import search_agent
from agents.evaluator_agent import evaluator_agent
from agents.writer_agent import writer_agent


def should_continue_after_profile(state: AgentState) -> str:
    """Router: decide el siguiente nodo tras el profiler."""
    if state.get("error"):
        return "end"
    return "search"


def should_continue_after_search(state: AgentState) -> str:
    """Router: decide el siguiente nodo tras la búsqueda."""
    if state.get("error"):
        return "end"
    scholarships = state.get("raw_scholarships", [])
    if not scholarships:
        return "write"  # WriterAgent manejará el caso vacío
    return "evaluate"


def should_continue_after_evaluate(state: AgentState) -> str:
    """Router: decide el siguiente nodo tras la evaluación."""
    if state.get("error"):
        return "end"
    return "write"


def build_graph() -> StateGraph:
    """
    Construye y compila el grafo LangGraph multi-agente.

    Flujo:
        profiler → search → evaluate → writer → END

    Returns:
        Grafo compilado listo para invocar
    """
    graph = StateGraph(AgentState)

    # Registrar nodos (agentes)
    graph.add_node("profiler", profiler_agent)
    graph.add_node("search", search_agent)
    graph.add_node("evaluate", evaluator_agent)
    graph.add_node("write", writer_agent)

    # Definir punto de entrada
    graph.set_entry_point("profiler")

    # Definir transiciones condicionales
    graph.add_conditional_edges(
        "profiler",
        should_continue_after_profile,
        {"search": "search", "end": END},
    )
    graph.add_conditional_edges(
        "search",
        should_continue_after_search,
        {"evaluate": "evaluate", "write": "write", "end": END},
    )
    graph.add_conditional_edges(
        "evaluate",
        should_continue_after_evaluate,
        {"write": "write", "end": END},
    )

    # El writer siempre termina
    graph.add_edge("write", END)

    compiled = graph.compile()
    logger.info("✅ Grafo LangGraph compilado: profiler → search → evaluate → write → END")
    return compiled


# Singleton del grafo (se crea una sola vez)
scholarship_graph = build_graph()


def run_scholarship_search(user_input: str) -> AgentState:
    """
    Ejecuta el pipeline completo de búsqueda de becas.

    Args:
        user_input: Descripción del estudiante en texto libre

    Returns:
        Estado final del grafo con el reporte generado
    """
    logger.info(f"🚀 Iniciando búsqueda de becas para input: '{user_input[:80]}...'")

    initial_state: AgentState = {
        "user_input": user_input,
        "user_profile": None,
        "search_queries": [],
        "raw_scholarships": [],
        "evaluations": [],
        "report": None,
        "current_step": "profiler",
        "error": None,
        "messages": [
            {
                "role": "user",
                "content": user_input,
            }
        ],
    }

    final_state = scholarship_graph.invoke(initial_state)
    logger.info("✅ Pipeline completado")
    return final_state
