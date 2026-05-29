"""2_Monitor.py — System monitor: agents, hardware (GPU/CPU), scholarships."""
from __future__ import annotations
import json, sys, time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
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

st.set_page_config(page_title="System Monitor", page_icon="📊", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
[data-testid="stAppViewContainer"]{background:linear-gradient(135deg,#050505,#1a1a1a,#050505);}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#050505,#1a1a1a);border-right:1px solid rgba(157,255,0,0.35);}
[data-testid="stSidebarNav"]{display:none !important;}
[data-testid="stHeader"]{display:none !important;}
[data-testid="stToolbar"]{display:none !important;}
footer{visibility:hidden !important;}
.sec-hdr{display:flex;align-items:center;gap:.7rem;margin:1.5rem 0 1rem;padding-bottom:.7rem;border-bottom:1px solid rgba(157,255,0,0.25);}
.sec-title{font-size:1.2rem;font-weight:600;color:#e2e8f0;}
/* Agent cards */
.a-card{background:#1A1A1A;border:1px solid rgba(157,255,0,0.15);border-radius:12px;padding:1rem;transition:all .25s;}
.a-idle   {border-left:3px solid #334155;}
.a-running{border-left:3px solid #9DFF00;box-shadow:0 0 18px rgba(157,255,0,0.25);}
.a-done   {border-left:3px solid #22c55e;}
.a-error  {border-left:3px solid #ef4444;}
.a-icon{font-size:1.4rem;margin-bottom:.4rem;}
.a-name{font-size:.85rem;font-weight:600;color:#cbd5e1;}
.a-phase{font-size:.72rem;color:#475569;margin-bottom:.4rem;}
.sbadge{display:inline-flex;align-items:center;gap:.3rem;padding:.2rem .6rem;border-radius:20px;font-size:.7rem;font-weight:600;}
.s-idle   {background:rgba(51,65,85,.5);color:#64748b;}
.s-running{background:rgba(157,255,0,0.15);color:#9DFF00;animation:pulse 1.5s infinite;}
.s-done   {background:rgba(34,197,94,.15);color:#4ade80;}
.s-error  {background:rgba(239,68,68,.15);color:#f87171;}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.6}}
.a-msg{font-size:.7rem;color:#334155;font-family:'JetBrains Mono',monospace;margin-top:.4rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
/* Hardware card */
.hw-card{background:#1A1A1A;border:1px solid rgba(157,255,0,0.15);border-radius:16px;padding:1.5rem;margin-bottom:1rem;}
.hw-name{font-size:1rem;font-weight:600;color:#e2e8f0;margin-bottom:1rem;}
.hw-badge{display:inline-block;padding:.15rem .6rem;border-radius:6px;font-size:.7rem;font-weight:600;margin-left:.5rem;vertical-align:middle;}
.b-rocm  {background:rgba(239,68,68,.2);color:#fca5a5;}
.b-nvidia{background:rgba(34,197,94,.15);color:#86efac;}
.b-cpu   {background:rgba(66,133,244,.2);color:#93c5fd;}
.b-mock  {background:rgba(234,179,8,.15);color:#fde68a;}
.m-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1rem;}
.m-box{background:rgba(8,15,30,.8);border:1px solid rgba(157,255,0,0.25);border-radius:10px;padding:1rem;text-align:center;}
.m-val{font-size:1.8rem;font-weight:700;font-family:'JetBrains Mono',monospace;}
.m-lbl{font-size:.72rem;color:#475569;margin-top:.2rem;}
.m-util{color:#9DFF00;} .m-mem{color:#38bdf8;} .m-temp{color:#fb923c;} .m-pow{color:#4ade80;}
/* Backend banner */
.bk-banner{display:flex;align-items:center;gap:1rem;border-radius:14px;padding:1.2rem 1.5rem;margin-bottom:1.5rem;border:1px solid;}
/* Scholarship table */
.sr{display:grid;grid-template-columns:2fr 1.5fr .8fr .8fr .8fr;gap:.5rem;align-items:center;padding:.7rem 1rem;border-radius:8px;margin-bottom:.3rem;background:#1A1A1A;border:1px solid rgba(157,255,0,0.15);font-size:.85rem;transition:all .2s;}
.sr:hover{border-color:#9DFF00;background:rgba(157,255,0,0.05);}
.sh{font-size:.72rem;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;padding:.4rem 1rem;}
.sn{color:#cbd5e1;font-weight:500;} .si{color:#64748b;} .sc{color:#9DFF00;}
.so{color:#4ade80;} .scl{color:#f87171;} .sot{color:#facc15;}
.sd{color:#94a3b8;font-family:'JetBrains Mono',monospace;font-size:.78rem;}
.ts{font-size:.72rem;color:#334155;font-family:'JetBrains Mono',monospace;}
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
        if is_admin_user(u):
            st.page_link("pages/4_Admin.py", label="⚙️ Panel de Administración")
    except Exception:
        pass

    st.markdown("---")
    auto_refresh = st.toggle("Auto-refresh", value=True)
    interval = st.slider("Interval (s)", 2, 30, 5)
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()
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

now_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
st.markdown(f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;'>"
            f"<h1 style='color:#e2e8f0;margin:0;font-size:1.9rem;'>📊 System Monitor</h1>"
            f"<span class='ts'>Updated: {now_str}</span></div>", unsafe_allow_html=True)

# ── BACKEND BANNER ────────────────────────────────────────────────────────────
try:
    from frontend.utils.backend_info import get_backend_info
    bi = get_backend_info()
    hw = bi["hardware"]
    color = bi["color"]
    hw_label = (
        "⚡ GPU · AMD ROCm"       if hw == "gpu" else
        "☁️ CPU · Google Cloud"   if "gcp" in bi["provider"] else
        "🖥️ CPU · Local"
    )
    st.markdown(f"""
    <div class="bk-banner" style="background:rgba(15,23,42,.9);border-color:rgba(99,102,241,.3);">
        <span style="font-size:2.5rem;">{bi['icon']}</span>
        <div style="flex:1;">
            <div style="color:#e2e8f0;font-size:1.1rem;font-weight:600;">{bi['label']}</div>
            <div style="color:#64748b;font-size:.85rem;">{bi['desc']}</div>
            <div style="color:#818cf8;font-size:.8rem;margin-top:.2rem;">
                Model: <strong>{bi['model']}</strong> &nbsp;|&nbsp;
                Endpoint: <span style="color:#475569;">{bi['endpoint'] or 'localhost'}</span>
            </div>
        </div>
        <div style="text-align:right;">
            <div style="background:rgba(99,102,241,.15);color:#818cf8;border-radius:8px;padding:.4rem .9rem;font-size:.8rem;font-weight:600;">{hw_label}</div>
            <div style="color:#475569;font-size:.72rem;margin-top:.3rem;">Provider: {bi['provider']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
except Exception as e:
    st.warning(f"Could not load backend info: {e}")

# ── SECTION 1: AGENTS ─────────────────────────────────────────────────────────
st.markdown('<div class="sec-hdr"><span style="font-size:1.4rem;">🤖</span><span class="sec-title">Active Agents</span></div>', unsafe_allow_html=True)

try:
    from frontend.utils.agent_status import get_agent_statuses
    agents = get_agent_statuses()
except Exception as e:
    st.warning(f"Agent status unavailable: {e}")
    agents = []

_SI = {"idle":"⚪","running":"🟣","done":"🟢","error":"🔴"}
_SL = {"idle":"IDLE","running":"RUNNING","done":"DONE","error":"ERROR"}

if agents:
    for row_agents in [agents[:4], agents[4:]]:
        cols = st.columns(4)
        for col, a in zip(cols, row_agents):
            with col:
                msg = f'<div class="a-msg" title="{a.last_message}">{a.last_message[:80]}</div>' if a.last_message else ""
                ts  = f'<div class="ts" style="margin-top:.3rem;">{a.last_seen}</div>' if a.last_seen else ""
                st.markdown(f"""<div class="a-card a-{a.status}">
                    <div class="a-icon">{a.icon}</div>
                    <div class="a-name">{a.label}</div>
                    <div class="a-phase">{a.phase}</div>
                    <span class="sbadge s-{a.status}">{_SI[a.status]} {_SL[a.status]}</span>
                    {msg}{ts}</div>""", unsafe_allow_html=True)
    n_run = sum(1 for a in agents if a.status=="running")
    n_don = sum(1 for a in agents if a.status=="done")
    n_err = sum(1 for a in agents if a.status=="error")
    n_idl = sum(1 for a in agents if a.status=="idle")
    st.markdown(f'<div style="display:flex;gap:1.5rem;margin-top:.8rem;font-size:.85rem;">'
                f'<span style="color:#818cf8;">🟣 Running: {n_run}</span>'
                f'<span style="color:#4ade80;">🟢 Done: {n_don}</span>'
                f'<span style="color:#f87171;">🔴 Error: {n_err}</span>'
                f'<span style="color:#475569;">⚪ Idle: {n_idl}</span></div>', unsafe_allow_html=True)

# ── SECTION 2: HARDWARE ───────────────────────────────────────────────────────
try:
    from frontend.utils.backend_info import get_backend_info
    bi2 = get_backend_info()
    hw2 = bi2["hardware"]
except Exception:
    hw2 = "unknown"

hw_title = "⚡ GPU Status" if hw2 == "gpu" else "🖥️ Hardware / CPU Status"
st.markdown(f'<div class="sec-hdr" style="margin-top:2rem;"><span style="font-size:1.4rem;">{"⚡" if hw2=="gpu" else "🖥️"}</span><span class="sec-title">{hw_title}</span></div>', unsafe_allow_html=True)

try:
    from frontend.utils.gpu_monitor import get_gpu_info
    gpus = get_gpu_info()
except Exception as e:
    st.warning(f"Hardware info unavailable: {e}")
    gpus = []

for gpu in gpus:
    bc = f"b-{gpu.backend}"
    bl = {"rocm":"ROCm","nvidia":"CUDA","cpu":"CPU·GCP/Local","mock":"MOCK"}.get(gpu.backend, gpu.backend.upper())
    mem_lbl = "RAM" if gpu.backend == "cpu" else "VRAM"
    temp_html = (f'<div class="m-box"><div class="m-val m-temp">{gpu.temperature_c:.0f}°C</div>'
                 f'<div class="m-lbl">Temperature</div></div>') if gpu.backend != "cpu" else (
                 f'<div class="m-box"><div class="m-val" style="color:#4ade80;">N/A</div>'
                 f'<div class="m-lbl">Temperature (CPU)</div></div>')
    pow_html  = (f'<div class="m-box"><div class="m-val m-pow">{gpu.power_w:.0f}W</div>'
                 f'<div class="m-lbl">Power Draw</div></div>') if gpu.backend != "cpu" else (
                 f'<div class="m-box"><div class="m-val" style="color:#4ade80;">N/A</div>'
                 f'<div class="m-lbl">Power (CPU)</div></div>')
    util_lbl = "CPU Usage" if gpu.backend == "cpu" else "GPU Utilization"

    st.markdown(f"""<div class="hw-card">
        <div class="hw-name">{"⚡" if gpu.backend in ("rocm","nvidia") else "🖥️"} {gpu.name}
            <span class="hw-badge {bc}">{bl}</span></div>
        <div class="m-grid">
            <div class="m-box"><div class="m-val m-util">{gpu.utilization_pct:.0f}%</div><div class="m-lbl">{util_lbl}</div></div>
            <div class="m-box"><div class="m-val m-mem">{gpu.memory_pct:.1f}%</div>
                <div class="m-lbl">{mem_lbl} ({gpu.memory_used_mb/1024:.1f} / {gpu.memory_total_mb/1024:.1f} GB)</div></div>
            {temp_html}{pow_html}
        </div></div>""", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**{util_lbl}**")
        st.progress(min(gpu.utilization_pct / 100, 1.0))
    with c2:
        st.write(f"**{mem_lbl} Usage**")
        st.progress(min(gpu.memory_pct / 100, 1.0))

# ── SECTION 3: SCHOLARSHIPS ───────────────────────────────────────────────────
st.markdown('<div class="sec-hdr" style="margin-top:2rem;"><span style="font-size:1.4rem;">🎓</span><span class="sec-title">Registered Scholarships</span></div>', unsafe_allow_html=True)

sc1, sc2 = st.columns([5,1])
with sc1:
    mq = st.text_input("Semantic filter", placeholder="Filter by meaning, e.g. 'STEM scholarships Germany'…", label_visibility="collapsed", key="mq")
with sc2:
    do_f = st.button("🔍 Filter", use_container_width=True)

try:
    from database.repository import list_recent_scholarships
    raw_s = list_recent_scholarships(limit=200)
except Exception as e:
    st.error(f"Could not load scholarships: {e}")
    raw_s = []

if mq.strip() and do_f:
    with st.spinner("🤖 Applying semantic filter…"):
        try:
            from frontend.utils.scholarship_search import semantic_search_scholarships
            disp = semantic_search_scholarships(mq, limit=200, top_k=50)
        except Exception as e:
            st.warning(f"Semantic filter failed: {e}")
            disp = raw_s
else:
    disp = raw_s

n_open = sum(1 for s in raw_s if "open" in (s.get("application_status") or "").lower())
n_closed = sum(1 for s in raw_s if (s.get("application_status") or "").lower() in ("closed","expired"))
st.markdown(f'<div style="display:flex;gap:2rem;margin-bottom:1rem;font-size:.85rem;">'
            f'<span style="color:#818cf8;">📊 Total: <strong style="color:#e2e8f0;">{len(raw_s)}</strong></span>'
            f'<span style="color:#38bdf8;">👁 Showing: <strong style="color:#e2e8f0;">{len(disp)}</strong></span>'
            f'<span style="color:#4ade80;">✅ Open: <strong style="color:#e2e8f0;">{n_open}</strong></span>'
            f'<span style="color:#f87171;">❌ Closed: <strong style="color:#e2e8f0;">{n_closed}</strong></span></div>', unsafe_allow_html=True)

if not disp:
    st.info("No scholarships in the knowledge base yet. Run: `uv run python main.py --rank-scholarships`")
else:
    st.markdown('<div class="sr sh"><div>Scholarship Name</div><div>Institution</div><div>Country</div><div>Status</div><div>Deadline</div></div>', unsafe_allow_html=True)
    for s in disp[:100]:
        name    = (s.get("scholarship_name") or "—")[:60]
        inst    = (s.get("institution") or "—")[:40]
        country = s.get("country") or "—"
        raw_st  = (s.get("application_status") or "unknown").lower()
        deadline= (s.get("deadline") or "—")[:15]
        url     = s.get("source_url") or ""
        sc_cls, sc_lbl = (
            ("so","🟢 Open")   if "open"   in raw_st else
            ("scl","🔴 Closed") if raw_st in ("closed","expired") else
            ("sot",f"🟡 {raw_st.capitalize()}")
        )
        def get_country_flag(country: str) -> str:
            c = str(country or "").strip().lower()
            flags = {
                "ecuador": "🇪🇨",
                "colombia": "🇨🇴",
                "peru": "🇵🇪",
                "venezuela": "🇻🇪",
                "argentina": "🇦🇷",
                "chile": "🇨🇱",
                "canada": "🇨🇦",
                "germany": "🇩🇪",
                "spain": "🇪🇸",
                "united kingdom": "🇬🇧",
                "uk": "🇬🇧",
                "france": "🇫🇷",
                "netherlands": "🇳🇱",
                "united states": "🇺🇸",
                "usa": "🇺🇸",
                "global": "🌍",
                "todo el mundo": "🌍",
            }
            for k, flag in flags.items():
                if k in c:
                    return f"{flag} {country}"
            return f"🌍 {country}"

        name_html = f'<a href="{url}" target="_blank" style="color:#94a3b8;text-decoration:none;">{name}</a>' if url else name
        st.markdown(f'<div class="sr"><div class="sn">{name_html}</div><div class="si">{inst}</div>'
                    f'<div class="sc">{get_country_flag(country)}</div><div class="{sc_cls}">{sc_lbl}</div>'
                    f'<div class="sd">{deadline}</div></div>', unsafe_allow_html=True)
    if len(disp) > 100:
        st.caption(f"Showing 100 of {len(disp)}. Use semantic filter to narrow down.")

if auto_refresh:
    time.sleep(interval)
    st.rerun()
