"""
MultiAgentic-Becas — About Page
AMD Developer Hackathon 2026 | Track 1: AI Agents
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

st.set_page_config(page_title="About | MultiAgentic-Becas", page_icon="⚡", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}

.hero{background:linear-gradient(135deg,#0D1117 0%,#1a0a0a 50%,#0D1117 100%);
  border:1px solid #2a1010;border-radius:20px;padding:2.8rem 2.5rem;margin-bottom:2rem;position:relative;overflow:hidden;}
.hero::before{content:'';position:absolute;top:-60px;right:-60px;width:280px;height:280px;
  background:radial-gradient(circle,rgba(237,28,36,.15) 0%,transparent 70%);border-radius:50%;}
.hero-badge{display:inline-block;background:linear-gradient(90deg,#ED1C24,#FF6B35);color:white;
  padding:.3rem 1rem;border-radius:30px;font-size:.78rem;font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;margin-bottom:.9rem;}
.hero-title{font-size:2.8rem;font-weight:800;
  background:linear-gradient(135deg,#ED1C24 0%,#FF6B35 55%,#FFD700 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0 0 .4rem;line-height:1.1;}
.hero-sub{color:#9CA3AF;font-size:1.1rem;margin:0;}

.sec{font-size:1.4rem;font-weight:700;color:#F9FAFB;margin:0 0 1rem;
  padding-bottom:.4rem;border-bottom:2px solid #ED1C24;display:inline-block;}

.stat-block{background:#111827;border:1px solid #1F2937;border-radius:12px;padding:1rem;text-align:center;}
.stat-num{font-size:1.9rem;font-weight:800;
  background:linear-gradient(90deg,#ED1C24,#FF6B35);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.stat-lbl{color:#6B7280;font-size:.78rem;margin-top:.15rem;}

.card{background:linear-gradient(135deg,#111827,#0f1a2e);
  border:1px solid #1F2937;border-left:4px solid #ED1C24;
  border-radius:14px;padding:1.3rem 1.2rem;margin-bottom:.9rem;}
.card-title{color:#F9FAFB;font-weight:700;font-size:.98rem;margin-bottom:.35rem;}
.card-body{color:#9CA3AF;font-size:.85rem;line-height:1.65;}

.perk{background:#111827;border:1px solid #1F2937;border-radius:14px;
  padding:1.2rem 1rem;text-align:center;margin-bottom:.8rem;}
.perk:hover{border-color:#ED1C24;}
.perk-icon{font-size:1.9rem;margin-bottom:.35rem;}
.perk-title{color:#F9FAFB;font-weight:700;font-size:.88rem;margin-bottom:.2rem;}
.perk-desc{color:#6B7280;font-size:.78rem;line-height:1.5;}

/* Phase table */
.phase-table{width:100%;border-collapse:collapse;font-size:.84rem;}
.phase-table th{background:#1F2937;color:#9CA3AF;font-weight:600;padding:.55rem .9rem;
  text-align:left;border-bottom:1px solid #374151;}
.phase-table td{padding:.5rem .9rem;border-bottom:1px solid #1F2937;color:#D1D5DB;vertical-align:top;}
.phase-table tr:hover td{background:rgba(237,28,36,.04);}
.phase-num{color:#ED1C24;font-weight:700;}
.phase-comp{color:#FF6B35;font-weight:600;}
.phase-desc{color:#9CA3AF;}

/* Pipeline nodes */
.pnode{background:#111827;border:1px solid #374151;border-radius:9px;
  padding:.6rem .5rem;text-align:center;color:#E5E7EB;font-size:.78rem;font-weight:600;margin:.18rem 0;}
.pnode.llm{background:rgba(237,28,36,.1);border-color:#ED1C24;color:#FF6B6B;}
.pnode.kb{background:rgba(59,130,246,.1);border-color:#3B82F6;color:#93C5FD;font-size:.82rem;font-weight:700;}
.pnode.out{background:rgba(16,185,129,.1);border-color:#10B981;color:#6EE7B7;}
.pnode.sub{font-size:.72rem;border-style:dashed;color:#9CA3AF;margin:.12rem 0;}
.parrow{text-align:center;color:#6B7280;font-size:1rem;margin:.08rem 0;line-height:1;}

/* Profile fields */
.field-pill{display:inline-block;background:#1F2937;color:#D1D5DB;
  border:1px solid #374151;padding:.28rem .85rem;border-radius:20px;
  font-size:.78rem;font-weight:600;margin:.22rem;}

/* Tech pills */
.tpill{display:inline-block;background:#1F2937;color:#D1D5DB;
  border:1px solid #374151;padding:.26rem .8rem;border-radius:20px;font-size:.77rem;font-weight:600;margin:.2rem;}
.tpill.amd{background:rgba(237,28,36,.15);border-color:#ED1C24;color:#FF6B6B;}

.cta{background:linear-gradient(135deg,#1a0505,#0D1117);border:1px solid #ED1C24;
  border-radius:16px;padding:2rem;text-align:center;margin-top:1.5rem;}
.cta-title{color:#F9FAFB;font-size:1.35rem;font-weight:700;margin-bottom:.4rem;}
.cta-sub{color:#9CA3AF;font-size:.92rem;}

.sbadge{background:linear-gradient(90deg,#ED1C24,#FF6B35);color:white;
  padding:.25rem .75rem;border-radius:6px;font-size:.74rem;font-weight:600;}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<span class="sbadge">⚡ AMD Hackathon 2026</span>', unsafe_allow_html=True)
    st.markdown("### 🤖 Track 1: AI Agents")
    st.markdown("---")
    st.markdown("**15 Fases de desarrollo:**")
    phases = [
        "Base Project & CLI", "Local Qwen (Ollama)", "Profile Intelligence",
        "Query Generation", "Web Search", "Source Intelligence",
        "Page Reading", "Scholarship Extraction", "Knowledge Base",
        "RAG & Retrieval", "Eligibility & Matching", "Ranking",
        "Refresh & Scalability", "AMD Cloud / vLLM", "Hackathon Demo",
    ]
    for i, p in enumerate(phases, 1):
        st.markdown(f"`{i:02d}` {p}")
    st.markdown("---")
    st.markdown("**LLM:** 🤖 Qwen via Ollama")
    st.markdown("**DB:** 🗄️ SQLite + RAG")

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-badge">⚡ AMD Developer Hackathon 2026</div>
  <h1 class="hero-title">MultiAgentic-Becas</h1>
  <p class="hero-sub">
    Búsqueda inteligente de becas académicas · 15 fases de pipeline agentico ·
    <strong style="color:#FF6B35">Track 1: AI Agents &amp; Agentic Workflows</strong>
  </p>
</div>
""", unsafe_allow_html=True)

# ── Stats ─────────────────────────────────────────────────────────────────────
for col, (n, l) in zip(st.columns(4), [
    ("15", "Fases del Pipeline"), ("10", "Campos de Perfil"),
    ("Qwen", "LLM via Ollama"), ("MI300X", "GPU AMD"),
]):
    with col:
        st.markdown(f'<div class="stat-block"><div class="stat-num">{n}</div>'
                    f'<div class="stat-lbl">{l}</div></div>', unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

# ── Hackathon info + Track ────────────────────────────────────────────────────
c1, c2 = st.columns([3, 2], gap="large")
with c1:
    st.markdown('<p class="sec">🏆 Sobre el Hackathon</p>', unsafe_allow_html=True)
    st.markdown("""
    <div style="color:#D1D5DB;font-size:.92rem;line-height:1.8;">
    El <strong style="color:#FF6B35">AMD Developer Hackathon</strong> es un evento hands-on para
    developers, founders y builders que quieren llevar al límite lo que es posible con IA
    en infraestructura real. Todo corre <strong style="color:#FFD700">100% en la nube</strong>,
    sin necesidad de hardware propio.
    </div>""", unsafe_allow_html=True)
    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown('<p class="sec">🎁 Beneficios</p>', unsafe_allow_html=True)
    pa, pb = st.columns(2)
    for i, (icon, title, desc) in enumerate([
        ("💳", "$100 en créditos", "AMD Developer Cloud — AMD AI Developer Program"),
        ("🖥️", "AMD Instinct MI300X", "GPUs de última generación en la nube"),
        ("📚", "Cursos de IA", "Tutoriales y recursos curados"),
        ("🎓", "DeepLearning.AI Pro", "Membresía complementaria de 1 mes"),
        ("☁️", "100% Cloud", "Sin hardware requerido"),
    ]):
        col = pa if i % 2 == 0 else pb
        with col:
            st.markdown(f'<div class="perk"><div class="perk-icon">{icon}</div>'
                        f'<div class="perk-title">{title}</div>'
                        f'<div class="perk-desc">{desc}</div></div>', unsafe_allow_html=True)

with c2:
    st.markdown('<p class="sec">🤖 Track 1</p>', unsafe_allow_html=True)
    for title, body in [
        ("🎯 Objetivo", "Construir sistemas de IA sofisticados más allá del RAG simple: agentes que automatizan flujos y asisten en problemas complejos."),
        ("🛠️ Tech Stack", "LangChain · Qwen via Ollama · SQLite · RAG Retrieval · FastAPI · Streamlit"),
        ("⚡ Compute", "$100 en créditos AMD Developer Cloud · AMD Instinct MI300X · ROCm"),
    ]:
        st.markdown(f'<div class="card"><div class="card-title">{title}</div>'
                    f'<div class="card-body">{body}</div></div>', unsafe_allow_html=True)

    st.markdown('<p class="sec">🔧 Tech Stack</p>', unsafe_allow_html=True)
    st.markdown("".join(
        f'<span class="tpill {c}">{n}</span>' for c, n in [
            ("amd","AMD MI300X"),("amd","ROCm"),("amd","AMD Cloud"),
            ("","Qwen via Ollama"),("","LangChain"),("","SQLite"),
            ("","RAG Retrieval"),("","FastAPI"),("","Streamlit"),("","Python 3.11"),
        ]
    ), unsafe_allow_html=True)

st.markdown("---")

# ── 15-Phase Roadmap ──────────────────────────────────────────────────────────
st.markdown('<p class="sec">🗺️ Roadmap — 15 Fases de Desarrollo</p>', unsafe_allow_html=True)

phases_data = [
    (1,  "Base Project and Local CLI",        "Creates the system foundation"),
    (2,  "Local Qwen Integration",            "Connects Qwen locally via Ollama"),
    (3,  "Profile Intelligence Layer",        "Prepares and normalizes the user profile"),
    (4,  "Query Generation Agent",            "Generates intelligent search queries"),
    (5,  "Web Search Layer",                  "Searches for pages on the Internet"),
    (6,  "Source Intelligence Layer",         "Validates the quality of sources"),
    (7,  "Page Reading and Cleaning",         "Reads and cleans web pages"),
    (8,  "Scholarship Extraction Agent",      "Extracts scholarships from text"),
    (9,  "Scholarship Knowledge Base",        "Stores reusable knowledge"),
    (10, "RAG and Retrieval Layer",           "Retrieves already known scholarships"),
    (11, "Eligibility and Matching Layer",    "Compares the profile against each scholarship"),
    (12, "Ranking and Recommendation Layer",  "Ranks and recommends scholarships"),
    (13, "Refresh and Global Scalability",    "Updates scholarships and prepares scalability"),
    (14, "AMD Cloud / vLLM Compatibility",   "Prepares future cloud compatibility"),
    (15, "Hackathon Technical Demo",          "Runs the final technical demo"),
]

rows = "".join(
    f'<tr><td class="phase-num">{n}</td>'
    f'<td class="phase-comp">{comp}</td>'
    f'<td class="phase-desc">{desc}</td></tr>'
    for n, comp, desc in phases_data
)
st.markdown(f"""
<table class="phase-table">
  <thead><tr><th>Phase</th><th>Component</th><th>What it does</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
""", unsafe_allow_html=True)

st.markdown("---")

# ── Profile Intelligence ───────────────────────────────────────────────────────
st.markdown('<p class="sec">🧠 Profile Intelligence Layer</p>', unsafe_allow_html=True)
st.markdown('<p style="color:#9CA3AF;font-size:.87rem;margin-bottom:1rem;">'
            'El usuario ingresa su perfil en lenguaje natural. El agente extrae y normaliza '
            '10 dimensiones clave hacia un <strong style="color:#FF6B35">Normalized Profile JSON</strong>.</p>',
            unsafe_allow_html=True)

fields = ["🌍 Nationality","🏠 Country of residence","🗣️ Languages and level",
          "🎓 Academic level","📚 Field of study","💡 Interests",
          "✈️ Target countries","🏦 Scholarship type","💰 Budget","📐 Preferred modality"]

st.markdown(
    '<div style="text-align:center;background:#111827;border:1px solid #1F2937;'
    'border-radius:14px;padding:1.2rem;">'
    '<div style="color:#F9FAFB;font-weight:700;font-size:.95rem;margin-bottom:.8rem;">'
    '📥 User enters profile</div>'
    + "".join(f'<span class="field-pill">{f}</span>' for f in fields)
    + '<div style="margin:.9rem 0;color:#ED1C24;font-size:1.2rem;">▼</div>'
    '<div style="background:rgba(59,130,246,.1);border:1px solid #3B82F6;border-radius:10px;'
    'padding:.6rem 1.2rem;display:inline-block;color:#93C5FD;font-weight:700;font-size:.9rem;">'
    '🗂️ Normalized Profile JSON</div></div>',
    unsafe_allow_html=True
)

st.markdown("---")

# ── Full Pipeline Flow ────────────────────────────────────────────────────────
st.markdown('<p class="sec">🔄 Pipeline de Datos Completo</p>', unsafe_allow_html=True)
st.markdown('<p style="color:#9CA3AF;font-size:.87rem;margin-bottom:1.2rem;">'
            'Motor de razonamiento: <strong style="color:#FF6B35">Local Qwen via Ollama</strong>. '
            'El pipeline bifurca entre búsqueda nueva y recuperación del Knowledge Base.</p>',
            unsafe_allow_html=True)

left_col, _, right_col = st.columns([2, 0.1, 1.2])

def nd(label, cls=""):
    return f'<div class="pnode {cls}">{label}</div>'

def arr():
    return '<div class="parrow">▼</div>'

with left_col:
    st.markdown(f"""
    <div style="max-width:360px;margin:0 auto;">
      {nd("📥 Normalized Profile")}
      {arr()}
      {nd("🔎 Query Generation Agent")}
      {arr()}
      {nd("🌐 Web Search")}
      {arr()}
      {nd("📡 Source Validation")}
      {arr()}
      {nd("📄 Page Reading")}
      {arr()}
      {nd("🔬 Scholarship Extraction")}
      {arr()}
      {nd("🗃️ Save to Scholarship Knowledge Base", "kb")}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    # KB sub-items
    kb_cols = st.columns(4)
    for col, lbl in zip(kb_cols, ["📚 Stored Scholarships","🔗 Stored Sources","🔍 Stored Queries","👤 Profile History"]):
        with col:
            st.markdown(f'<div class="pnode sub">{lbl}</div>', unsafe_allow_html=True)

with right_col:
    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="max-width:280px;">
      {nd("🤖 Local Qwen<br/>via Ollama", "llm")}
      <div style="color:#6B7280;font-size:.7rem;text-align:center;margin:.3rem 0 .8rem;">
        ↙ Query Gen &nbsp;|&nbsp; ↙ Source Val<br/>
        ↙ Extraction &nbsp;|&nbsp; ↙ Eligibility
      </div>
      <div style="margin-top:.5rem;"></div>
      {nd("🔄 New Profile Search (RAG path)")}
      {arr()}
      {nd("🔍 Retrieval Layer")}
      <div style="color:#6B7280;font-size:.7rem;text-align:center;margin:.2rem 0;">
        ← pulls from Knowledge Base
      </div>
      {arr()}
      {nd("♻️ Reuse known scholarships if relevant")}
      {arr()}
      {nd("⚖️ Eligibility and Matching")}
      {arr()}
      {nd("🏆 Ranking")}
      {arr()}
      {nd("✅ Final Recommendations", "out")}
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ── Components ────────────────────────────────────────────────────────────────
st.markdown('<p class="sec">🏗️ Componentes del Sistema</p>', unsafe_allow_html=True)
comp_cols = st.columns(3)
for col, (title, bc, tc, body) in zip(comp_cols, [
    ("🤖 LLM Engine", "#ED1C24", "#FF6B6B",
     "<strong>Local Qwen via Ollama</strong><br/><br/>"
     "• Query Generation Agent<br/>• Source Intelligence<br/>"
     "• Scholarship Extraction<br/>• Eligibility &amp; Matching"),
    ("🗃️ Knowledge Base", "#3B82F6", "#93C5FD",
     "<strong>SQLite + RAG Retrieval</strong><br/><br/>"
     "• Stored Scholarships<br/>• Stored Sources &amp; Queries<br/>"
     "• Profile History<br/>• Refresh &amp; Scalability Layer"),
    ("⚡ AMD Cloud", "#10B981", "#34D399",
     "<strong>MI300X + ROCm (Phase 14)</strong><br/><br/>"
     "• vLLM Compatibility<br/>• $100 en créditos<br/>"
     "• Web Search paralela<br/>• Hackathon Technical Demo"),
]):
    with col:
        st.markdown(
            f'<div class="card" style="border-left-color:{bc};">'
            f'<div class="card-title" style="color:{tc};">{title}</div>'
            f'<div class="card-body">{body}</div></div>',
            unsafe_allow_html=True
        )

# ── CTA ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="cta">
  <div class="cta-title">🚀 ¿Listo para encontrar tu beca ideal?</div>
  <div class="cta-sub">Describe tu perfil en lenguaje natural · 10 dimensiones analizadas ·
  Pipeline de 15 fases · Powered by AMD MI300X</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)
st.markdown("""
<hr style="border-color:#1F2937;"/>
<p style="text-align:center;color:#374151;font-size:.77rem;">
  MultiAgentic-Becas · AMD Developer Hackathon 2026 · Track 1: AI Agents &amp; Agentic Workflows<br/>
  Qwen via Ollama · SQLite · RAG Retrieval · AMD Instinct MI300X · ROCm
</p>
""", unsafe_allow_html=True)
