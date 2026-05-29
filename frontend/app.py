"""app.py — Home page for DevIALabs Streamlit UI."""
from __future__ import annotations
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import importlib
for mod in [
    "auth.session",
    "database.repository",
    "frontend.utils.profile_ui",
    "frontend.utils.header_ui",
    "frontend.utils.auth_ui",
    "frontend.utils.backend_info",
    "frontend.utils.scholarship_search",
    "frontend.utils.agent_status",
    "frontend.utils.gpu_monitor",
    "frontend.utils.application_export"
]:
    if mod in sys.modules:
        try:
            importlib.reload(sys.modules[mod])
        except Exception:
            pass

import streamlit as st

st.set_page_config(page_title="DevIALabs", page_icon="🎓", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
[data-testid="stAppViewContainer"]{background:linear-gradient(135deg,#050505,#1a1a1a,#050505);}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#050505,#1a1a1a);border-right:1px solid rgba(157,255,0,0.35);}
[data-testid="stSidebarNav"]{display:none !important;}
[data-testid="stHeader"]{display:none !important;}
[data-testid="stToolbar"]{display:none !important;}
footer{visibility:hidden !important;}
.hero{background:linear-gradient(135deg,rgba(157,255,0,0.08),rgba(157,255,0,0.03));border:1px solid rgba(157,255,0,0.3);border-radius:20px;padding:1.5rem 2rem;text-align:center;margin-bottom:1rem;}
.hero-title{font-size:2.6rem;font-weight:700;background:linear-gradient(135deg,#9DFF00,#ffffff,#9DFF00);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.hero-sub{font-size:1rem;color:#94a3b8;margin-bottom:1rem;}
.badge{display:inline-block;background:rgba(157,255,0,0.15);color:#9DFF00;border:1px solid rgba(157,255,0,0.3);border-radius:50px;padding:.3rem 1rem;font-size:.8rem;font-weight:600;margin:.15rem;}
.stat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin:1rem 0;}
.stat-card{background:#1A1A1A;border:1px solid rgba(157,255,0,0.15);border-radius:14px;padding:0.8rem 1rem;text-align:center;transition:all .3s;}
.stat-card:hover{border-color:#9DFF00;transform:translateY(-2px);box-shadow:0 8px 30px rgba(157,255,0,0.15);}
.stat-num{font-size:2rem;font-weight:700;color:#9DFF00;}
.stat-lbl{font-size:.8rem;color:#94a3b8;margin-top:.2rem;}
.backend-bar{display:flex;align-items:center;gap:1rem;background:#1A1A1A;border-radius:12px;padding:1rem 1.5rem;margin-bottom:1.5rem;border:1px solid rgba(157,255,0,0.25);}
div.stButton > button {
    background-color: #1A1A1A !important;
    color: #F5F5F5 !important;
    border: 1px solid rgba(157,255,0,0.3) !important;
}
div.stButton > button:hover {
    background-color: #9DFF00 !important;
    color: #050505 !important;
    border: 1px solid #9DFF00 !important;
    box-shadow: 0 4px 15px rgba(157,255,0,0.3);
}
div.stButton > button[kind="primary"] {
    background-color: #9DFF00 !important;
    color: #050505 !important;
    border: 1px solid #9DFF00 !important;
    font-weight: 600 !important;
}
div.stButton > button[kind="primary"]:hover {
    background-color: #ffffff !important;
    color: #050505 !important;
    border: 1px solid #ffffff !important;
    box-shadow: 0 4px 15px rgba(255,255,255,0.3);
}
</style>
""", unsafe_allow_html=True)

# ── Handle OAuth callback if it lands on home ─────────────────────────────────
try:
    from auth.session import get_current_user as _get_user
    _get_user()   # processes ?code= params if present, stores session token
except Exception:
    pass

with st.sidebar:
    st.markdown("## <span style='color:#9DFF00;'>Dev</span><span style='color:white;'>IA</span><span style='color:#9DFF00;'>Labs</span>", unsafe_allow_html=True)
    st.caption("Scholarship & Internship Intelligent Platform")
    st.markdown("---")
    st.page_link("app.py", label="🏠 Home")
    st.page_link("pages/1_Search_Scholarships.py", label="🔍 Search Scholarships")
    st.page_link("pages/3_Apply_Scholarship.py", label="📝 Apply to Scholarship")
    st.page_link("pages/2_Monitor.py", label="📊 System Monitor")
    
    # Conditional admin gating in sidebar
    try:
        from auth.session import get_current_user, is_admin_user
        u = get_current_user()
        if u:
            st.sidebar.write(f"Logged in as: {u.email}")
            st.sidebar.write(f"Is Admin: {is_admin_user(u)}")
        if is_admin_user(u):
            st.page_link("pages/4_Admin.py", label="⚙️ Panel de Administración")
    except Exception as e:
        st.sidebar.error(f"Error admin link: {e}")

    st.markdown("---")
    try:
        from frontend.utils.auth_ui import render_auth_sidebar
        render_auth_sidebar()
    except Exception:
        pass


# Initialize applied scholarships session state
if "applied_scholarships" not in st.session_state:
    st.session_state["applied_scholarships"] = []

# Render premium top header
try:
    from frontend.utils.header_ui import render_custom_header
    render_custom_header()
except Exception:
    pass


# Backend indicator
try:
    from frontend.utils.backend_info import get_backend_info
    bi = get_backend_info()
    hw_icon = "⚡ GPU" if bi["hardware"] == "gpu" else ("☁️ CPU·GCP" if bi["hardware"] == "cpu" and "gcp" in bi["provider"] else "🖥️ CPU·Local")
    st.markdown(f"""
    <div class="backend-bar">
        <span style="font-size:1.8rem;">{bi['icon']}</span>
        <div>
            <div style="color:#e2e8f0;font-weight:600;">{bi['label']}</div>
            <div style="color:#64748b;font-size:.8rem;">{bi['desc']} &nbsp;|&nbsp; Model: <span style="color:#9DFF00;">{bi['model']}</span></div>
        </div>
        <span style="margin-left:auto;background:rgba(157,255,0,0.15);color:#9DFF00;border-radius:8px;padding:.3rem .8rem;font-size:.75rem;font-weight:600;">{hw_icon}</span>
    </div>
    """, unsafe_allow_html=True)
except Exception:
    pass

st.markdown("""
<div class="hero">
    <div class="hero-title">🎓 Becas DevIALabs</div>
    <div class="hero-sub">Sistema multi-agente de IA para el descubrimiento inteligente de becas</div>
    <span class="badge">🤖 Pipeline LangGraph</span>
    <span class="badge">☁️ CPU GCP</span>
    <span class="badge">🔍 Búsqueda Semántica</span>
</div>
""", unsafe_allow_html=True)

try:
    from database.repository import list_recent_scholarships
    ss = list_recent_scholarships(limit=1000)
    n_s  = len(ss)
    n_c  = len({s.get("country","") for s in ss if s.get("country")})
    n_a  = sum(1 for s in ss if "open" in (s.get("application_status") or "").lower())
    n_i  = len({s.get("institution","") for s in ss if s.get("institution")})
except Exception:
    n_s = n_c = n_a = n_i = 0

st.markdown(f"""
<div class="stat-grid">
    <div class="stat-card"><div class="stat-num">{n_s}</div><div class="stat-lbl">Becas en Base de Datos</div></div>
    <div class="stat-card"><div class="stat-num">{n_c}</div><div class="stat-lbl">Países Cubiertos</div></div>
    <div class="stat-card"><div class="stat-num">{n_a}</div><div class="stat-lbl">Convocatorias Activas (Abiertas)</div></div>
    <div class="stat-card"><div class="stat-num">{n_i}</div><div class="stat-lbl">Instituciones</div></div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")
from auth.session import get_current_user
from database.repository import get_user

user = get_current_user()
is_premium = False
if user:
    try:
        db_user = get_user(user.sub)
        if db_user and db_user.get("is_premium") == 1:
            is_premium = True
    except Exception:
        pass

if is_premium:
    if st.button("🔍 Buscar Internships / Becas", type="primary", use_container_width=True):
        st.switch_page("pages/1_Search_Scholarships.py")
else:
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("🔍 Buscar Internships", type="secondary", use_container_width=True):
            st.switch_page("pages/1_Search_Scholarships.py")
    with btn_col2:
        if st.button("✨ Aplicar (Premium)", type="primary", use_container_width=True):
            st.switch_page("pages/3_Apply_Scholarship.py")
