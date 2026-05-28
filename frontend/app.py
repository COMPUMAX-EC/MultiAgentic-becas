"""app.py — Home page for MultiAgentic Scholarships Streamlit UI."""
from __future__ import annotations
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

st.set_page_config(page_title="MultiAgentic Scholarships", page_icon="🎓", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
[data-testid="stAppViewContainer"]{background:linear-gradient(135deg,#0a0e1a,#0f172a,#1a1035);}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0d1321,#141b2d);border-right:1px solid #1e293b;}
.hero{background:linear-gradient(135deg,rgba(99,102,241,.15),rgba(139,92,246,.1));border:1px solid rgba(99,102,241,.3);border-radius:20px;padding:3rem 2.5rem;text-align:center;margin-bottom:2rem;}
.hero-title{font-size:3rem;font-weight:700;background:linear-gradient(135deg,#818cf8,#c084fc,#38bdf8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.hero-sub{font-size:1.1rem;color:#94a3b8;margin-bottom:1.5rem;}
.badge{display:inline-block;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white;border-radius:50px;padding:.4rem 1.2rem;font-size:.85rem;font-weight:500;margin:.2rem;}
.stat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin:2rem 0;}
.stat-card{background:rgba(15,23,42,.8);border:1px solid rgba(99,102,241,.2);border-radius:14px;padding:1.5rem;text-align:center;transition:all .3s;}
.stat-card:hover{border-color:rgba(99,102,241,.5);transform:translateY(-2px);}
.stat-num{font-size:2.2rem;font-weight:700;color:#818cf8;}
.stat-lbl{font-size:.85rem;color:#64748b;margin-top:.3rem;}
.backend-bar{display:flex;align-items:center;gap:1rem;background:rgba(15,23,42,.9);border-radius:12px;padding:1rem 1.5rem;margin-bottom:1.5rem;border:1px solid rgba(99,102,241,.25);}
</style>
""", unsafe_allow_html=True)

# ── Handle OAuth callback if it lands on home ─────────────────────────────────
try:
    from auth.session import get_current_user as _get_user
    _get_user()   # processes ?code= params if present, stores session token
except Exception:
    pass

with st.sidebar:
    st.markdown("### 🎓 MultiAgentic\n**Scholarships**")
    st.markdown("---")
    st.page_link("app.py", label="🏠 Home")
    st.page_link("pages/1_Search_Scholarships.py", label="🔍 Search Scholarships")
    st.page_link("pages/3_Apply_Scholarship.py", label="📝 Apply to Scholarship")
    st.page_link("pages/2_Monitor.py", label="📊 System Monitor")
    st.markdown("---")
    st.caption("AMD Developer Hackathon 2026")
    try:
        from frontend.utils.auth_ui import render_auth_sidebar
        render_auth_sidebar()
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
            <div style="color:#64748b;font-size:.8rem;">{bi['desc']} &nbsp;|&nbsp; Model: <span style="color:#818cf8;">{bi['model']}</span></div>
        </div>
        <span style="margin-left:auto;background:rgba(99,102,241,.15);color:#818cf8;border-radius:8px;padding:.3rem .8rem;font-size:.75rem;font-weight:600;">{hw_icon}</span>
    </div>
    """, unsafe_allow_html=True)
except Exception:
    pass

st.markdown("""
<div class="hero">
    <div class="hero-title">🎓 MultiAgentic Scholarships</div>
    <div class="hero-sub">AI-powered multi-agent system for intelligent scholarship discovery</div>
    <span class="badge">🤖 LangGraph Pipeline</span>
    <span class="badge">⚡ AMD MI300X</span>
    <span class="badge">☁️ GCP CPU</span>
    <span class="badge">🔍 Semantic Search</span>
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
    <div class="stat-card"><div class="stat-num">{n_s}</div><div class="stat-lbl">Scholarships in KB</div></div>
    <div class="stat-card"><div class="stat-num">{n_c}</div><div class="stat-lbl">Countries Covered</div></div>
    <div class="stat-card"><div class="stat-num">{n_a}</div><div class="stat-lbl">Active (Open)</div></div>
    <div class="stat-card"><div class="stat-num">{n_i}</div><div class="stat-lbl">Institutions</div></div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")
c1, c2 = st.columns(2)
with c1:
    st.info("🔍 Go to **Search Scholarships** to find matching opportunities.")
with c2:
    st.info("📊 Go to **System Monitor** to watch agents, hardware, and the KB.")
