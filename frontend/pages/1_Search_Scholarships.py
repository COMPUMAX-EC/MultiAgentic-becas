"""1_Search_Scholarships.py — Semantic scholarship search page."""
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
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🎓 MultiAgentic\n**Scholarships**")
    st.markdown("---")
    st.page_link("app.py", label="🏠 Home")
    st.page_link("pages/1_Search_Scholarships.py", label="🔍 Search Scholarships")
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

st.markdown("<h1 style='color:#e2e8f0;font-size:1.9rem;'>🔍 Search Scholarships</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#64748b;'>Describe what you're looking for — the AI model semantically ranks scholarships from the knowledge base.</p>", unsafe_allow_html=True)

query = st.text_area("Query", placeholder="e.g. 'Colombian systems engineering student looking for a fully funded master's in AI in Europe'", height=90, label_visibility="collapsed")
c1, c2 = st.columns([1,6])
with c1:
    search = st.button("🔍 Search", type="primary", use_container_width=True)

if search and query.strip():
    with st.spinner("🤖 Running semantic search…"):
        try:
            from frontend.utils.scholarship_search import semantic_search_scholarships
            results = semantic_search_scholarships(query, limit=scan, top_k=top_k)
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
            status = (s.get("application_status") or "unknown").lower()
            sc = "tag-open" if "open" in status else ("tag-closed" if status in ("closed","expired") else "tag-l")
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
                <span class="tag {sc}">● {status}</span>{fields}</div>
                <div style="margin-top:.7rem;display:flex;gap:1.5rem;">{dl_html}{url_html}</div>
                {reason_html}</div>""", unsafe_allow_html=True)
elif not query.strip():
    st.markdown("<div style='text-align:center;padding:3rem;color:#475569;'><div style='font-size:4rem;'>🔍</div><div style='margin-top:1rem;font-size:1.1rem;'>Type a query above and press Search.</div></div>", unsafe_allow_html=True)
