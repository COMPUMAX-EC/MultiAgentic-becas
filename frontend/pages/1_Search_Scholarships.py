"""1_Search_Scholarships.py — Semantic scholarship search page (auth + quota gated)."""
from __future__ import annotations
import json, sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

st.set_page_config(page_title="Search Scholarships", page_icon="🔍", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
[data-testid="stAppViewContainer"]{background:linear-gradient(135deg,#0a0e1a,#0f172a,#1a1035);}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0d1321,#141b2d);border-right:1px solid #1e293b;}
.s-card{background:rgba(15,23,42,.85);border:1px solid rgba(99,102,241,.2);border-radius:14px;padding:1.5rem;margin-bottom:1rem;position:relative;overflow:hidden;transition:all .25s;}
.s-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#6366f1,#8b5cf6,#38bdf8);}
.s-card:hover{border-color:rgba(99,102,241,.5);box-shadow:0 8px 30px rgba(99,102,241,.12);transform:translateY(-2px);}
.s-title{font-size:1.1rem;font-weight:600;color:#e2e8f0;}
.s-inst{font-size:.9rem;color:#818cf8;margin-bottom:.6rem;}
.tag{display:inline-block;padding:.2rem .7rem;border-radius:20px;font-size:.75rem;font-weight:500;margin:.15rem;}
.tag-c{background:rgba(56,189,248,.15);color:#38bdf8;border:1px solid rgba(56,189,248,.3);}
.tag-l{background:rgba(99,102,241,.15);color:#818cf8;border:1px solid rgba(99,102,241,.3);}
.tag-open{background:rgba(34,197,94,.15);color:#4ade80;border:1px solid rgba(34,197,94,.3);}
.tag-closed{background:rgba(239,68,68,.15);color:#f87171;border:1px solid rgba(239,68,68,.3);}
.tag-f{background:rgba(139,92,246,.12);color:#c084fc;border:1px solid rgba(139,92,246,.25);}
.reason{background:rgba(99,102,241,.08);border-left:3px solid #6366f1;border-radius:0 8px 8px 0;padding:.5rem 1rem;margin-top:.8rem;font-size:.83rem;color:#94a3b8;font-style:italic;}
.quota-bar-wrap{background:rgba(15,23,42,.8);border:1px solid rgba(99,102,241,.2);border-radius:10px;padding:.7rem 1rem;margin-bottom:1rem;display:flex;align-items:center;gap:1rem;}
.quota-exhausted{background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.3);border-radius:14px;padding:2rem;text-align:center;margin-top:2rem;}
</style>
""", unsafe_allow_html=True)

# ── Auth: process OAuth callback before UI ───────────────────────────────────
try:
    from auth.session import get_current_user
    from auth.quota import QuotaExceededError, consume_query, get_quota_status
    from frontend.utils.profile_ui import (
        build_search_query,
        profile_is_complete,
        render_profile_editor,
    )
    _AUTH_AVAILABLE = True
    _user_early = get_current_user()
except ImportError:
    _AUTH_AVAILABLE = False
    _user_early = None

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎓 MultiAgentic\n**Scholarships**")
    st.markdown("---")
    st.page_link("app.py", label="🏠 Home")
    st.page_link("pages/1_Search_Scholarships.py", label="🔍 Search Scholarships")
    st.page_link("pages/3_Apply_Scholarship.py", label="📝 Apply to Scholarship")
    st.page_link("pages/2_Monitor.py", label="📊 System Monitor")
    st.markdown("---")
    top_k = st.slider("Max results", 3, 20, 10)
    scan  = st.slider("Scholarships to scan", 10, 200, 50)
    try:
        from frontend.utils.backend_info import get_backend_info
        bi = get_backend_info()
        st.markdown(f"""<div style="background:rgba(15,23,42,.8);border-radius:8px;padding:.6rem .8rem;margin-top:.5rem;font-size:.78rem;">
            {bi['icon']} <strong style="color:#e2e8f0;">{bi['label']}</strong><br>
            <span style="color:#64748b;">{bi['model']}</span>
        </div>""", unsafe_allow_html=True)
    except Exception:
        pass
    # Auth widget
    try:
        from frontend.utils.auth_ui import render_auth_sidebar
        render_auth_sidebar()
    except Exception:
        pass

# ── Auth gate — login only in sidebar when logged out ────────────────────────
if _AUTH_AVAILABLE:
    from auth.session import require_login
    user = require_login(sidebar_only=True)
else:
    user = None

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("<h1 style='color:#e2e8f0;font-size:1.9rem;'>🔍 Search Scholarships</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='color:#64748b;'>Completa tu perfil y busca hasta "
    "<strong style='color:#818cf8;'>5 becas por día</strong> según tu perfil académico.</p>",
    unsafe_allow_html=True,
)

# ── Academic profile (per user) ───────────────────────────────────────────────
_profile: dict = {}
_profile_ok = True
if _AUTH_AVAILABLE and user:
    _profile = render_profile_editor(user.sub)
    _profile_ok = profile_is_complete(_profile)
    if not _profile_ok:
        st.warning(
            "Guarda tu perfil con los campos obligatorios (*) antes de buscar becas."
        )

# ── Daily quota banner ────────────────────────────────────────────────────────
_quota_ok = True
if _AUTH_AVAILABLE and user:
    status    = get_quota_status(user.sub)
    used      = status["used"]
    limit     = status["limit"]
    remaining = status["remaining"]
    pct       = int((used / limit) * 100)
    qcolor    = "#4ade80" if remaining > 2 else ("#facc15" if remaining > 0 else "#ef4444")

    st.markdown(
        f"<div class='quota-bar-wrap'>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;justify-content:space-between;font-size:.78rem;"
        f"color:#64748b;margin-bottom:.35rem;'>"
        f"<span>🔎 Daily search quota</span>"
        f"<span style='color:{qcolor};font-weight:600;'>{used} / {limit} used</span>"
        f"</div>"
        f"<div style='background:rgba(30,41,59,.8);border-radius:6px;height:7px;overflow:hidden;'>"
        f"<div style='width:{pct}%;height:100%;background:{qcolor};"
        f"border-radius:6px;transition:width .4s;'></div>"
        f"</div></div>"
        f"<div style='font-size:.72rem;color:#334155;white-space:nowrap;'>"
        f"{'✅ ' + str(remaining) + ' left' if remaining > 0 else '⛔ Quota reached'}"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    if remaining <= 0:
        _quota_ok = False
        st.markdown(
            f"""
<div class='quota-exhausted'>
  <div style='font-size:2.5rem;margin-bottom:.5rem;'>⛔</div>
  <div style='font-size:1.1rem;font-weight:600;color:#f87171;margin-bottom:.4rem;'>
    Daily limit reached
  </div>
  <div style='color:#64748b;font-size:.9rem;'>
    You've used all <strong style='color:#f87171;'>{limit} searches</strong> for today.<br>
    Your quota resets automatically after <strong>24 hours</strong>.
  </div>
</div>""",
            unsafe_allow_html=True,
        )

# ── Search form ───────────────────────────────────────────────────────────────
query = st.text_area(
    "Query",
    placeholder="Preferencias extra (opcional): ej. 'beca full funding en IA, deadline 2026'",
    height=70,
    label_visibility="collapsed",
    disabled=not _quota_ok or not _profile_ok,
)
c1, c2 = st.columns([1, 6])
with c1:
    search = st.button(
        "🔍 Search",
        type="primary",
        use_container_width=True,
        disabled=not _quota_ok or not _profile_ok,
    )

# ── Execute search ────────────────────────────────────────────────────────────
if search and _quota_ok and _profile_ok:
    search_text = build_search_query(_profile, query)
    if _AUTH_AVAILABLE and user:
        try:
            consume_query(user.sub, search_text)
        except QuotaExceededError as qe:
            st.error(f"⛔ {qe}")
            st.stop()

    with st.spinner("🤖 Running semantic search…"):
        try:
            from frontend.utils.scholarship_search import semantic_search_scholarships
            results = semantic_search_scholarships(
                search_text,
                limit=scan,
                top_k=top_k,
                profile=_profile,
            )
        except Exception as e:
            st.error(f"Search error: {e}")
            results = []

    if not results:
        st.info("No scholarships found. Run the pipeline first: `uv run python main.py --rank-scholarships`")
    else:
        st.markdown(f"**{len(results)} scholarship{'s' if len(results)!=1 else ''} found**")
        st.markdown("---")
        def pl(v):
            if isinstance(v, list): return v
            try: return json.loads(v or "[]")
            except: return []
        for s in results:
            status_val = (s.get("application_status") or "unknown").lower()
            sc = "tag-open" if "open" in status_val else ("tag-closed" if status_val in ("closed","expired") else "tag-l")
            fields = "".join(f'<span class="tag tag-f">{f}</span>' for f in pl(s.get("fields_json") or s.get("fields",[]))[:4])
            reason_html = f'<div class="reason">✨ {s.get("relevance_reason","")}</div>' if s.get("relevance_reason") else ""
            url = s.get("source_url","")
            url_html = f'<a href="{url}" target="_blank" style="color:#38bdf8;font-size:.8rem;">🔗 View →</a>' if url else ""
            dl = s.get("deadline","")
            dl_html = f'<span style="color:#facc15;font-size:.8rem;">📅 {dl}</span>' if dl else ""
            st.markdown(f"""<div class="s-card">
                <div class="s-title">{s.get('scholarship_name','—')}</div>
                <div class="s-inst">{s.get('institution','')}</div>
                <div><span class="tag tag-c">🌍 {s.get('country','—')}</span>
                <span class="tag tag-l">🎓 {s.get('academic_level','—')}</span>
                <span class="tag {sc}">● {status_val}</span>{fields}</div>
                <div style="margin-top:.7rem;display:flex;gap:1.5rem;">{dl_html}{url_html}</div>
                {reason_html}</div>""", unsafe_allow_html=True)
            if _AUTH_AVAILABLE and user:
                if st.button(
                    "📝 Preparar postulación",
                    key=f"apply_{s.get('scholarship_hash', s.get('scholarship_name', ''))}",
                ):
                    st.session_state["apply_scholarship"] = dict(s)
                    st.switch_page("pages/3_Apply_Scholarship.py")

elif _quota_ok and _profile_ok:
    st.markdown(
        "<div style='text-align:center;padding:3rem;color:#475569;'>"
        "<div style='font-size:4rem;'>🔍</div>"
        "<div style='margin-top:1rem;font-size:1.1rem;'>"
        "Perfil listo — pulsa Search para encontrar becas acordes a tu perfil."
        "</div></div>",
        unsafe_allow_html=True,
    )
