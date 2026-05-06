"""
MultiAgentic-Becas — Tests básicos de agentes
"""
import pytest
from unittest.mock import patch, MagicMock

from models.schemas import UserProfile, AcademicLevel, LanguageSkill, LanguageProficiency
from models.state import AgentState


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_profile() -> UserProfile:
    return UserProfile(
        name="Juan Pérez",
        academic_level=AcademicLevel.MASTER,
        field_of_study="Computer Science",
        country_of_origin="Colombia",
        target_countries=["Germany", "Netherlands"],
        gpa=8.5,
        languages=[
            LanguageSkill(language="Spanish", proficiency=LanguageProficiency.NATIVE),
            LanguageSkill(language="English", proficiency=LanguageProficiency.ADVANCED),
        ],
        financial_need=True,
        career_goals="AI research in healthcare",
    )


@pytest.fixture
def sample_state(sample_profile) -> AgentState:
    return {
        "user_input": "Soy colombiano, ingeniero de sistemas, quiero hacer maestría en IA en Europa",
        "user_profile": sample_profile,
        "search_queries": [],
        "raw_scholarships": [],
        "evaluations": [],
        "report": None,
        "current_step": "profiler",
        "error": None,
        "messages": [],
    }


# ─── Tests de schemas ────────────────────────────────────────────────────────

def test_user_profile_creation(sample_profile):
    """Verifica que el UserProfile se crea correctamente."""
    assert sample_profile.academic_level == AcademicLevel.MASTER
    assert sample_profile.country_of_origin == "Colombia"
    assert sample_profile.gpa == 8.5
    assert len(sample_profile.languages) == 2


def test_user_profile_gpa_validation():
    """Verifica validación de GPA fuera de rango."""
    with pytest.raises(ValueError):
        UserProfile(
            academic_level=AcademicLevel.MASTER,
            field_of_study="CS",
            country_of_origin="Colombia",
            gpa=11.0,  # Fuera del rango 0-10
        )


def test_agent_state_structure(sample_state):
    """Verifica que el AgentState tiene todos los campos requeridos."""
    required_keys = [
        "user_input", "user_profile", "search_queries",
        "raw_scholarships", "evaluations", "report",
        "current_step", "error", "messages",
    ]
    for key in required_keys:
        assert key in sample_state, f"Falta clave: {key}"


# ─── Tests de orchestrator ────────────────────────────────────────────────────

def test_orchestrator_routing():
    """Verifica que el grafo se construye sin errores."""
    from agents.orchestrator import scholarship_graph
    assert scholarship_graph is not None


@patch("agents.profiler_agent.get_llm")
def test_profiler_agent_error_handling(mock_llm):
    """Verifica manejo de errores cuando el LLM retorna JSON inválido."""
    mock_response = MagicMock()
    mock_response.content = "esto no es json válido"
    mock_llm.return_value.invoke.return_value = mock_response

    from agents.profiler_agent import profiler_agent

    state: AgentState = {
        "user_input": "Soy estudiante de maestría",
        "user_profile": None,
        "search_queries": [],
        "raw_scholarships": [],
        "evaluations": [],
        "report": None,
        "current_step": "profiler",
        "error": None,
        "messages": [],
    }

    result = profiler_agent(state)
    assert result.get("error") is not None
    assert result.get("current_step") == "error"
