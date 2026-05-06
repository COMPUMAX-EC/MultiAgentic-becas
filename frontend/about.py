"""
MultiAgentic-Becas — About Page
Página informativa sobre el AMD Developer Hackathon y el proyecto.
"""
import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="About | MultiAgentic-Becas",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* Hero */
  .hero-wrapper {
    background: linear-gradient(135deg, #0D1117 0%, #1a0a0a 50%, #0D1117 100%);
    border: 1px solid #2a1010;
    border-radius: 20px;
    padding: 3rem 2.5rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
  }
  .hero-wrapper::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(237,28,36,0.15) 0%, transparent 70%);
    border-radius: 50%;
  }
  .hero-title {
    font-size: 3rem;
    font-weight: 800;
    background: linear-gradient(135deg, #ED1C24 0%, #FF6B35 55%, #FFD700 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 0.4rem 0;
    line-height: 1.1;
  }
  .hero-sub {
    color: #9CA3AF;
    font-size: 1.15rem;
    margin: 0 0 1.5rem 0;
  }
  .hero-badge {
    display: inline-block;
    background: linear-gradient(90deg, #ED1C24, #FF6B35);
    color: white;
    padding: 0.35rem 1rem;
    border-radius: 30px;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 1rem;
  }

  /* Section title */
  .section-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #F9FAFB;
    margin: 0 0 1rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #ED1C24;
    display: inline-block;
  }

  /* Perk card */
  .perk-card {
    background: #111827;
    border: 1px solid #1F2937;
    border-radius: 14px;
    padding: 1.4rem 1.2rem;
    text-align: center;
    transition: border-color 0.2s;
    height: 100%;
  }
  .perk-card:hover { border-color: #ED1C24; }
  .perk-icon { font-size: 2.2rem; margin-bottom: 0.5rem; }
  .perk-title { color: #F9FAFB; font-weight: 700; font-size: 0.95rem; margin-bottom: 0.3rem; }
  .perk-desc { color: #6B7280; font-size: 0.82rem; line-height: 1.5; }

  /* Track card */
  .track-card {
    background: linear-gradient(135deg, #111827, #0f1a2e);
    border: 1px solid #1F2937;
    border-left: 4px solid #ED1C24;
    border-radius: 14px;
    padding: 1.5rem 1.3rem;
    margin-bottom: 1rem;
  }
  .track-title { color: #F9FAFB; font-weight: 700; font-size: 1.05rem; margin-bottom: 0.5rem; }
  .track-body { color: #9CA3AF; font-size: 0.88rem; line-height: 1.6; }

  /* Agent pipeline */
  .agent-step {
    background: #111827;
    border: 1px solid #1F2937;
    border-radius: 12px;
    padding: 1.2rem;
    text-align: center;
    position: relative;
  }
  .agent-step-num {
    position: absolute;
    top: -12px; left: 50%;
    transform: translateX(-50%);
    background: linear-gradient(90deg, #ED1C24, #FF6B35);
    color: white;
    width: 26px; height: 26px;
    border-radius: 50%;
    font-size: 0.75rem;
    font-weight: 700;
    display: flex; align-items: center; justify-content: center;
  }
  .agent-icon { font-size: 2rem; margin: 0.6rem 0 0.4rem; }
  .agent-name { color: #F9FAFB; font-weight: 700; font-size: 0.9rem; }
  .agent-role { color: #6B7280; font-size: 0.78rem; margin-top: 0.2rem; }

  /* Tech pill */
  .tech-pill {
    display: inline-block;
    background: #1F2937;
    color: #D1D5DB;
    border: 1px solid #374151;
    padding: 0.3rem 0.9rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    margin: 0.25rem;
  }
  .tech-pill.amd {
    background: rgba(237,28,36,0.15);
    border-color: #ED1C24;
    color: #FF6B6B;
  }

  /* Stats bar */
  .stat-block {
    background: #111827;
    border: 1px solid #1F2937;
    border-radius: 12px;
    padding: 1.2rem;
    text-align: center;
  }
  .stat-num {
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(90deg, #ED1C24, #FF6B35);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .stat-label { color: #6B7280; font-size: 0.82rem; margin-top: 0.2rem; }

  /* CTA */
  .cta-box {
    background: linear-gradient(135deg, #1a0505, #0D1117);
    border: 1px solid #ED1C24;
    border-radius: 16px;
    padding: 2rem;
    text-align: center;
    margin-top: 2rem;
  }
  .cta-title { color: #F9FAFB; font-size: 1.4rem; font-weight: 700; margin-bottom: 0.5rem; }
  .cta-sub { color: #9CA3AF; font-size: 0.95rem; margin-bottom: 1.2rem; }

  /* Sidebar */
  .sidebar-badge {
    background: linear-gradient(90deg, #ED1C24, #FF6B35);
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
  }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<span class="sidebar-badge">⚡ AMD Developer Hackathon 2026</span>', unsafe_allow_html=True)
    st.markdown("### 🤖 Track 1: AI Agents")
    st.markdown("---")
    st.markdown("**Sistema multi-agente:**")
    st.markdown("1. 🎓 **ProfilerAgent** — Analiza tu perfil")
    st.markdown("2. 🔍 **SearchAgent** — Busca becas")
    st.markdown("3. ⚖️ **EvaluatorAgent** — Calcula compatibilidad")
    st.markdown("4. ✍️ **WriterAgent** — Genera tu reporte")
    st.markdown("---")
    st.markdown("**LLM:** 🔴 LLaMA 3.1 70B vía AMD MI300X")
    st.markdown("**Orquestación:** 🔗 LangGraph StateGraph")
    st.markdown("---")
    if st.button("🚀 Ir a la App", use_container_width=True, type="primary"):
        st.switch_page("frontend/app.py")

# ─── Hero ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-wrapper">
  <div class="hero-badge">⚡ AMD Developer Hackathon 2026</div>
  <h1 class="hero-title">MultiAgentic-Becas</h1>
  <p class="hero-sub">
    Búsqueda inteligente de becas académicas con agentes IA orquestados en AMD Developer Cloud.<br/>
    Construido para el <strong style="color:#FF6B35">Track 1: AI Agents &amp; Agentic Workflows</strong>.
  </p>
</div>
""", unsafe_allow_html=True)

# ─── Stats ────────────────────────────────────────────────────────────────────
s1, s2, s3, s4 = st.columns(4)
stats = [
    ("4", "Agentes IA"),
    ("MI300X", "GPU AMD"),
    ("LLaMA 3.1 70B", "Modelo LLM"),
    ("LangGraph", "Orquestación"),
]
for col, (num, label) in zip([s1, s2, s3, s4], stats):
    with col:
        st.markdown(f"""
        <div class="stat-block">
          <div class="stat-num">{num}</div>
          <div class="stat-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

# ─── Sobre el Hackathon ───────────────────────────────────────────────────────
col_left, col_right = st.columns([3, 2], gap="large")

with col_left:
    st.markdown('<p class="section-title">🏆 Sobre el Hackathon</p>', unsafe_allow_html=True)
    st.markdown("""
    <div style="color:#D1D5DB; font-size:0.95rem; line-height:1.8;">
    El <strong style="color:#FF6B35">AMD Developer Hackathon</strong> es un evento hands-on para 
    developers, founders, engineers y builders que quieren llevar al límite lo que es posible con 
    IA en infraestructura real.<br/><br/>
    En el centro de todo: <strong style="color:#FFD700">AI Agents</strong> — un espacio para explorar 
    flujos de trabajo inteligentes, automatización y aplicaciones de IA reales. Todo corre 
    100% en la nube, sin necesidad de hardware propio.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown('<p class="section-title">🎁 Lo que reciben los participantes</p>', unsafe_allow_html=True)

    perks = [
        ("💳", "$100 en créditos", "AMD Developer Cloud para miembros del AMD AI Developer Program"),
        ("🖥️", "AMD Instinct MI300X", "Acceso a GPUs de última generación en la nube"),
        ("📚", "Cursos de IA", "Cursos y tutoriales curados de inteligencia artificial"),
        ("🎓", "DeepLearning.AI Pro", "Membresía complementaria de 1 mes"),
        ("☁️", "100% en la nube", "Sin hardware requerido — solo construye"),
    ]

    p1, p2 = st.columns(2)
    for i, (icon, title, desc) in enumerate(perks):
        col = p1 if i % 2 == 0 else p2
        with col:
            st.markdown(f"""
            <div class="perk-card" style="margin-bottom:0.8rem;">
              <div class="perk-icon">{icon}</div>
              <div class="perk-title">{title}</div>
              <div class="perk-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

with col_right:
    st.markdown('<p class="section-title">🤖 Track 1: AI Agents</p>', unsafe_allow_html=True)
    st.markdown("""
    <div class="track-card">
      <div class="track-title">🎯 Objetivo</div>
      <div class="track-body">
        Construir sistemas de IA sofisticados más allá del RAG simple: 
        agentes que automatizan flujos, coordinan tareas y asisten en 
        problemas complejos.
      </div>
    </div>
    <div class="track-card">
      <div class="track-title">🛠️ Tech Stack</div>
      <div class="track-body">
        LangChain · CrewAI · AutoGen conectados a modelos open-source 
        como Llama, DeepSeek, Mistral y Qwen.
      </div>
    </div>
    <div class="track-card">
      <div class="track-title">⚡ Compute</div>
      <div class="track-body">
        $100 en créditos AMD Developer Cloud con acceso a GPUs 
        AMD Instinct MI300X.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown('<p class="section-title">🔧 Tech Stack del Proyecto</p>', unsafe_allow_html=True)
    tech_items = [
        ("amd", "AMD MI300X"),
        ("amd", "ROCm"),
        ("amd", "AMD Developer Cloud"),
        ("", "LangGraph"),
        ("", "LangChain"),
        ("", "LLaMA 3.1 70B"),
        ("", "FastAPI"),
        ("", "Streamlit"),
        ("", "Python 3.11"),
        ("", "Pydantic v2"),
    ]
    pills_html = "".join(
        f'<span class="tech-pill {cls}">{name}</span>'
        for cls, name in tech_items
    )
    st.markdown(pills_html, unsafe_allow_html=True)

st.markdown("---")

# ─── Pipeline de Agentes ──────────────────────────────────────────────────────
st.markdown('<p class="section-title">🔄 Pipeline Multi-Agente</p>', unsafe_allow_html=True)
st.markdown(
    '<p style="color:#9CA3AF; font-size:0.9rem; margin-bottom:1.5rem;">'
    'Orquestado con <strong style="color:#FF6B35">LangGraph StateGraph</strong> — cada agente '
    'es un nodo con estado compartido y transiciones determinísticas.</p>',
    unsafe_allow_html=True
)

agents_data = [
    ("🎓", "ProfilerAgent", "Extrae y estructura el perfil académico del usuario desde texto libre"),
    ("🔍", "SearchAgent", "Genera queries optimizadas y busca becas en la web en tiempo real"),
    ("⚖️", "EvaluatorAgent", "Calcula score de compatibilidad beca-perfil con breakdown detallado"),
    ("✍️", "WriterAgent", "Genera reporte ejecutivo y borrador de carta de motivación"),
]

cols = st.columns(4)
for i, (icon, name, role) in enumerate(agents_data):
    with cols[i]:
        st.markdown(f"""
        <div class="agent-step">
          <div class="agent-step-num">{i+1}</div>
          <div class="agent-icon">{icon}</div>
          <div class="agent-name">{name}</div>
          <div class="agent-role">{role}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

# Flujo visual simple
flow_cols = st.columns([1, 0.15, 1, 0.15, 1, 0.15, 1])
flow_items = ["Input de usuario", "→", "Perfil estructurado", "→", "Becas rankeadas", "→", "Reporte + Carta"]
for col, item in zip(flow_cols, flow_items):
    with col:
        if item == "→":
            st.markdown(
                '<p style="text-align:center; color:#ED1C24; font-size:1.5rem; margin:0.8rem 0;">→</p>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div style="background:#111827; border:1px solid #1F2937; border-radius:8px; '
                f'padding:0.6rem; text-align:center; color:#D1D5DB; font-size:0.82rem;">{item}</div>',
                unsafe_allow_html=True
            )

st.markdown("---")

# ─── Arquitectura ─────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">🏗️ Arquitectura del Sistema</p>', unsafe_allow_html=True)

arch_col1, arch_col2, arch_col3 = st.columns(3)

with arch_col1:
    st.markdown("""
    <div class="track-card" style="border-left-color: #3B82F6;">
      <div class="track-title" style="color:#60A5FA;">🖥️ Frontend</div>
      <div class="track-body">
        <strong>Streamlit</strong> — UI interactiva con progreso en tiempo real<br/><br/>
        • Formulario de perfil libre<br/>
        • Progress tracker por agente<br/>
        • Tabs: Becas · Reporte · Carta<br/>
        • Download de documentos
      </div>
    </div>
    """, unsafe_allow_html=True)

with arch_col2:
    st.markdown("""
    <div class="track-card" style="border-left-color: #10B981;">
      <div class="track-title" style="color:#34D399;">⚙️ Backend</div>
      <div class="track-body">
        <strong>FastAPI + LangGraph</strong> — Orquestación robusta<br/><br/>
        • REST API en /v1/search<br/>
        • StateGraph determinístico<br/>
        • Pydantic v2 schemas<br/>
        • Logging con Loguru
      </div>
    </div>
    """, unsafe_allow_html=True)

with arch_col3:
    st.markdown("""
    <div class="track-card" style="border-left-color: #ED1C24;">
      <div class="track-title" style="color:#FF6B6B;">🔴 AMD Cloud</div>
      <div class="track-body">
        <strong>MI300X + ROCm</strong> — Inferencia de alto rendimiento<br/><br/>
        • LLaMA 3.1 70B vía API<br/>
        • AMD Developer Cloud<br/>
        • $100 en créditos<br/>
        • Latencia optimizada
      </div>
    </div>
    """, unsafe_allow_html=True)

# ─── CTA ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="cta-box">
  <div class="cta-title">🚀 ¿Listo para encontrar tu beca ideal?</div>
  <div class="cta-sub">
    Describe tu perfil académico y deja que los agentes IA hagan el trabajo pesado.
    Powered by AMD MI300X en la nube.
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)
if st.button("🎓 Ir a la App → Buscar Becas", type="primary", use_container_width=True, key="cta_btn"):
    st.switch_page("frontend/app.py")

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("<br/><br/>", unsafe_allow_html=True)
st.markdown("""
<hr style="border-color:#1F2937;"/>
<p style="text-align:center; color:#374151; font-size:0.8rem;">
  MultiAgentic-Becas · Built for AMD Developer Hackathon 2026 · Track 1: AI Agents &amp; Agentic Workflows<br/>
  Powered by AMD Instinct MI300X · LangGraph · LLaMA 3.1 70B · ROCm
</p>
""", unsafe_allow_html=True)
