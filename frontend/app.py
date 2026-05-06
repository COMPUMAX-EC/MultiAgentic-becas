"""
MultiAgentic-Becas — Frontend Streamlit
UI interactiva para buscar becas con el sistema multi-agente.
"""
import streamlit as st
import sys
import os

# Agregar el root del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import run_scholarship_search
from models.schemas import CompatibilityLevel

# ─── Configuración de página ────────────────────────────────────────────────

st.set_page_config(
    page_title="MultiAgentic-Becas | AMD Hackathon",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS personalizado ────────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main-title {
        background: linear-gradient(135deg, #ED1C24 0%, #FF6B35 50%, #FFD700 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        font-weight: 700;
        margin-bottom: 0;
    }

    .subtitle {
        color: #6B7280;
        font-size: 1.1rem;
        margin-top: 0.2rem;
    }

    .card-high {
        background: linear-gradient(135deg, #0f2027, #1a3a2a);
        border-left: 4px solid #22C55E;
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.8rem 0;
    }

    .card-medium {
        background: linear-gradient(135deg, #1a1a2e, #1a2a3a);
        border-left: 4px solid #F59E0B;
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.8rem 0;
    }

    .card-low {
        border-left: 4px solid #6B7280;
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.8rem 0;
        opacity: 0.8;
    }

    .score-badge {
        display: inline-block;
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
    }

    .amd-badge {
        background: linear-gradient(90deg, #ED1C24, #FF6B35);
        color: white;
        padding: 0.2rem 0.8rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .step-box {
        background: #1E293B;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        margin: 0.3rem 0;
        font-size: 0.9rem;
        border: 1px solid #334155;
    }
</style>
""", unsafe_allow_html=True)


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<span class="amd-badge">⚡ AMD Developer Hackathon 2026</span>', unsafe_allow_html=True)
    st.markdown("### 🤖 Track 1: AI Agents")
    st.markdown("---")
    st.markdown("**Sistema multi-agente:**")
    st.markdown("1. 🎓 **ProfilerAgent** — Analiza tu perfil")
    st.markdown("2. 🔍 **SearchAgent** — Busca becas")
    st.markdown("3. ⚖️ **EvaluatorAgent** — Calcula compatibilidad")
    st.markdown("4. ✍️ **WriterAgent** — Genera tu reporte")
    st.markdown("---")
    st.markdown("**LLM:**")
    st.markdown("🔴 LLaMA 3.1 70B vía AMD MI300X")
    st.markdown("**Orquestación:**")
    st.markdown("🔗 LangGraph StateGraph")


# ─── Header ──────────────────────────────────────────────────────────────────

st.markdown('<h1 class="main-title">🎓 MultiAgentic-Becas</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">Búsqueda inteligente de becas académicas con agentes IA orquestados '
    'en AMD Developer Cloud</p>',
    unsafe_allow_html=True,
)
st.markdown("---")


# ─── Formulario principal ─────────────────────────────────────────────────────

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### Cuéntame sobre ti")
    user_input = st.text_area(
        label="Describe tu perfil académico y objetivos:",
        placeholder=(
            "Ejemplo: Soy colombiano, ingeniero de sistemas con promedio de 4.2/5.0. "
            "Quiero hacer una maestría en Inteligencia Artificial en Europa o Estados Unidos. "
            "Hablo español nativo e inglés avanzado (TOEFL 105). "
            "Tengo 2 años de experiencia en startups de ML. "
            "Busco beca completa para 2026-2027."
        ),
        height=160,
        key="profile_input",
    )

    search_btn = st.button(
        "🚀 Buscar Becas con IA",
        type="primary",
        use_container_width=True,
    )

with col2:
    st.markdown("### 💡 Incluye en tu descripción:")
    tips = [
        "🎓 Nivel académico (maestría, PhD...)",
        "📚 Área de estudio",
        "🌍 País de origen",
        "✈️ Países de destino",
        "📊 Promedio académico",
        "🗣️ Idiomas y nivel",
        "💼 Experiencia previa",
        "🎯 Objetivos profesionales",
        "💰 ¿Necesitas beca completa?",
    ]
    for tip in tips:
        st.markdown(f'<div class="step-box">{tip}</div>', unsafe_allow_html=True)


# ─── Ejecutar búsqueda ────────────────────────────────────────────────────────

if search_btn and user_input.strip():
    st.markdown("---")

    # Progress tracking
    progress_container = st.container()
    with progress_container:
        st.markdown("### 🤖 Agentes trabajando...")
        prog_bar = st.progress(0)
        status_text = st.empty()

        col_agents = st.columns(4)
        agent_status = {
            "profiler": col_agents[0].empty(),
            "search": col_agents[1].empty(),
            "evaluate": col_agents[2].empty(),
            "write": col_agents[3].empty(),
        }

        agent_status["profiler"].info("🎓 Profiler\nAnalizando...")
        agent_status["search"].empty()
        agent_status["evaluate"].empty()
        agent_status["write"].empty()

        # Simular progreso visual mientras corre el pipeline
        import time

        def update_progress(step: str, pct: int, msg: str):
            prog_bar.progress(pct)
            status_text.markdown(f"**{msg}**")
            icons = {"profiler": "🎓", "search": "🔍", "evaluate": "⚖️", "write": "✍️"}
            labels = {
                "profiler": "Profiler\n✅ Listo",
                "search": "Search\nBuscando...",
                "evaluate": "Evaluator\nCalificando...",
                "write": "Writer\nRedactando...",
            }
            for a, widget in agent_status.items():
                if a < step or (a == step):
                    widget.success(f"{icons[a]} {labels[a]}")

        update_progress("profiler", 10, "ProfilerAgent analizando tu perfil...")
        time.sleep(0.5)

    # Ejecutar pipeline real
    try:
        with st.spinner(""):
            final_state = run_scholarship_search(user_input)

        prog_bar.progress(100)
        status_text.markdown("**✅ ¡Búsqueda completada!**")

        for widget in agent_status.values():
            widget.success("✅ Listo")

        # ─── Mostrar resultados ───────────────────────────────────────────────

        if final_state.get("error"):
            st.error(f"❌ Error: {final_state['error']}")
        else:
            report = final_state.get("report")
            evaluations = final_state.get("evaluations", [])

            st.markdown("---")

            # Métricas
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Becas Encontradas", len(evaluations))
            m2.metric(
                "Mejor Score",
                f"{evaluations[0].score}/100" if evaluations else "N/A"
            )
            high_count = sum(
                1 for e in evaluations
                if e.recommendation == CompatibilityLevel.HIGH
            )
            m3.metric("Alta Compatibilidad", high_count)
            m4.metric(
                "Tiene Carta",
                "✅ Sí" if (report and report.motivation_letter_draft) else "❌ No"
            )

            # Tabs de resultados
            tab1, tab2, tab3 = st.tabs(["📊 Becas Rankeadas", "📋 Reporte", "✉️ Carta de Motivación"])

            with tab1:
                if not evaluations:
                    st.warning("No se encontraron becas compatibles. Intenta ampliar tu descripción.")
                else:
                    for i, eval_ in enumerate(evaluations[:8]):
                        s = eval_.scholarship
                        color = (
                            "card-high" if eval_.recommendation == CompatibilityLevel.HIGH
                            else "card-medium" if eval_.recommendation == CompatibilityLevel.MEDIUM
                            else "card-low"
                        )
                        score_color = (
                            "#22C55E" if eval_.score >= 70
                            else "#F59E0B" if eval_.score >= 50
                            else "#6B7280"
                        )

                        st.markdown(f"""
<div class="{color}">
  <strong>#{i+1} — {s.name}</strong>
  <span style="float:right; background:{score_color}; color:white;
        padding:2px 10px; border-radius:12px; font-weight:700">
    {eval_.score}/100
  </span><br/>
  <small>🏛️ {s.provider} &nbsp;|&nbsp; 📅 {s.deadline or 'Sin fecha'} 
  &nbsp;|&nbsp; 💰 {s.funding_type}</small><br/><br/>
  <em>{s.description[:200]}...</em><br/><br/>
  ✅ <strong>Fortalezas:</strong> {', '.join(eval_.key_strengths[:3]) or 'N/A'}<br/>
  ⚠️ <strong>Brechas:</strong> {', '.join(eval_.key_gaps[:2]) or 'Ninguna'}<br/>
  <a href="{s.url}" target="_blank">🔗 Ver beca oficial</a>
</div>
""", unsafe_allow_html=True)

            with tab2:
                if report:
                    st.markdown("### Resumen Ejecutivo")
                    st.markdown(report.summary)

                    st.markdown("### 🏆 Top Recomendaciones")
                    for i, rec in enumerate(report.top_recommendations, 1):
                        st.markdown(f"**{i}.** {rec}")

                    st.markdown("### 📋 Próximos Pasos")
                    for step in report.next_steps:
                        st.markdown(f"- {step}")
                else:
                    st.info("No se generó reporte.")

            with tab3:
                if report and report.motivation_letter_draft:
                    st.markdown("### ✉️ Borrador de Carta de Motivación")
                    st.info(
                        "Este es un borrador generado por IA para la beca con mayor compatibilidad. "
                        "Personaliza los campos entre [corchetes] antes de usarla."
                    )
                    st.text_area(
                        label="Carta:",
                        value=report.motivation_letter_draft,
                        height=400,
                    )
                    st.download_button(
                        "⬇️ Descargar Carta",
                        data=report.motivation_letter_draft,
                        file_name="carta_motivacion.txt",
                        mime="text/plain",
                    )
                else:
                    st.info(
                        "La carta de motivación se genera automáticamente cuando hay una beca "
                        "con compatibilidad ALTA. Mejora tu perfil para activarla."
                    )

    except Exception as e:
        st.error(f"❌ Error inesperado: {e}")
        st.exception(e)

elif search_btn:
    st.warning("⚠️ Por favor describe tu perfil antes de buscar.")
