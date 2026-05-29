"""1_Search_Scholarships.py — Semantic scholarship search page (auth + quota gated)."""
from __future__ import annotations
import json, sys, re
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

st.set_page_config(page_title="Search Scholarships", page_icon="🔍", layout="wide")
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
.s-card{background:#1A1A1A;border:1px solid rgba(157,255,0,0.15);border-radius:14px;padding:1.5rem;margin-bottom:1rem;position:relative;overflow:hidden;transition:all .25s;}
.s-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#9DFF00,#ffffff,#9DFF00);}
.s-card:hover{border-color:#9DFF00;box-shadow:0 8px 30px rgba(157,255,0,0.12);transform:translateY(-2px);}
.s-title{font-size:1.1rem;font-weight:600;color:#e2e8f0;}
.s-inst{font-size:.9rem;color:#9DFF00;margin-bottom:.6rem;}
.tag{display:inline-block;padding:.2rem .7rem;border-radius:20px;font-size:.75rem;font-weight:500;margin:.15rem;}
.tag-c{background:rgba(157,255,0,0.15);color:#9DFF00;border:1px solid rgba(157,255,0,0.3);}
.tag-l{background:rgba(99,102,241,.15);color:#818cf8;border:1px solid rgba(99,102,241,.3);}
.tag-open{background:rgba(34,197,94,.15);color:#4ade80;border:1px solid rgba(34,197,94,.3);}
.tag-closed{background:rgba(239,68,68,.15);color:#f87171;border:1px solid rgba(239,68,68,.3);}
.tag-f{background:rgba(139,92,246,.12);color:#c084fc;border:1px solid rgba(139,92,246,.25);}
.reason{background:rgba(157,255,0,0.06);border-left:3px solid #9DFF00;border-radius:0 8px 8px 0;padding:.5rem 1rem;margin-top:.8rem;font-size:.83rem;color:#94a3b8;font-style:italic;}
.quota-bar-wrap{background:#1A1A1A;border:1px solid rgba(157,255,0,0.25);border-radius:10px;padding:.7rem 1rem;margin-bottom:1rem;display:flex;align-items:center;gap:1rem;}
.quota-exhausted{background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.3);border-radius:14px;padding:2rem;text-align:center;margin-top:2rem;}
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

# ── Profile helpers (needed for search even when auth is unavailable) ─────────
try:
    from frontend.utils.profile_ui import (
        build_search_query,
        profile_is_complete,
        render_profile_editor,
    )
except ImportError:
    def profile_is_complete(profile: dict) -> bool:
        return True

    def render_profile_editor(google_sub: str) -> dict:
        return {}

    def build_search_query(profile: dict, extra_query: str = "") -> str:
        return extra_query.strip()

# ── Auth: process OAuth callback before UI ───────────────────────────────────
try:
    from auth.session import get_current_user
    from auth.quota import QuotaExceededError, consume_query, get_quota_status
    _AUTH_AVAILABLE = True
    _user_early = get_current_user()
except ImportError:
    _AUTH_AVAILABLE = False
    _user_early = None

# ── Sidebar ──────────────────────────────────────────────────────────────────
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

# Initialize applied scholarships session state
if "applied_scholarships" not in st.session_state:
    st.session_state["applied_scholarships"] = []

# Render premium top header
try:
    from frontend.utils.header_ui import render_custom_header
    render_custom_header()
except Exception:
    pass


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
    placeholder="Preferencias extra (opcional: ej. 'beca de postgrado en Inteligencia Artificial')",
    height=70,
    label_visibility="collapsed",
    disabled=not _quota_ok or not _profile_ok,
)

st.markdown("##### ⚙️ Filtros adicionales")

# Extract dynamic filter options from raw_results
raw_results = st.session_state.get("search_results", [])

# Dynamic country filter
countries_found = sorted(list({s.get("country").strip().title() for s in raw_results if s.get("country")}))
if not countries_found:
    countries_found = ["Canada", "Germany", "Spain", "Colombia", "Ecuador", "United Kingdom", "United States"]
country_options = ["Todos"] + countries_found

# Dynamic academic level filter
levels_found = sorted(list({s.get("academic_level").strip().lower() for s in raw_results if s.get("academic_level")}))
if not levels_found:
    levels_found = ["high school", "bachelors", "masters", "phd"]

def format_level(lvl: str) -> str:
    mapping = {
        "high school": "Bachillerato / Secundaria",
        "bachelors": "Pregrado",
        "masters": "Maestría",
        "phd": "Doctorado"
    }
    return mapping.get(lvl.lower(), lvl.title())

level_options = ["Todos"] + [format_level(l) for l in levels_found]
level_display_to_raw = {format_level(l): l for l in levels_found}

f_col1, f_col2, f_col3 = st.columns(3)
with f_col1:
    filter_country = st.selectbox(
        "País de destino",
        country_options,
        key="filter_country"
    )
with f_col2:
    filter_level = st.selectbox(
        "Nivel académico",
        level_options,
        key="filter_level"
    )
with f_col3:
    filter_status = st.selectbox(
        "Estado de la convocatoria",
        ["Todos", "Abiertas", "Cerradas"],
        index=1,
        key="filter_status"
    )

st.markdown("##### 🔍 Búsqueda rápida y Ordenamiento")
s_col1, s_col2 = st.columns([2, 1])
with s_col1:
    filter_text = st.text_input(
        "Filtrar por palabra clave (nombre, institución, requisitos...)",
        placeholder="Ej: 'Inteligencia Artificial', 'Universidad'...",
        key="filter_text"
    )
with s_col2:
    sort_option = st.selectbox(
        "Ordenar resultados",
        ["Por relevancia (Defecto)", "Por fecha límite (Más cercanas)", "Alfabéticamente (A-Z)"],
        key="sort_option"
    )

c1, c2 = st.columns([1, 6])
with c1:
    search = st.button(
        "🔍 Buscar",
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
            # Initialize search logs
            search_logs = [
                f"⚙️ Generando consulta combinada con perfil...",
                f"📝 Texto de búsqueda: '{search_text}'",
                f"🗄️ Consultando base de datos local (límite de escaneo: {scan})..."
            ]
            results = semantic_search_scholarships(
                search_text,
                limit=scan,
                top_k=top_k,
                profile=_profile,
            )
            st.session_state["search_results"] = results
            search_logs.append(f"🤖 Enviando prompt de recomendación semántica al LLM...")
            search_logs.append(f"✨ Éxito: El modelo de IA ordenó y recomendó {len(results)} becas.")
            st.session_state["search_logs"] = search_logs
        except Exception as e:
            st.error(f"Search error: {e}")
            results = []
            st.session_state["search_logs"] = [f"❌ Error en la búsqueda: {str(e)}"]

raw_results = st.session_state.get("search_results", [])

# Show semantic search logs expander
search_logs = st.session_state.get("search_logs", [])
if search_logs:
    with st.expander("🛠️ Ver logs del proceso de búsqueda semántica", expanded=False):
        for log_line in search_logs:
            st.write(log_line)

# Apply filters
filtered_tuples = []
nats_filtered_count = 0

for idx, s in enumerate(raw_results):
    # Ensure the scholarship has a valid postulation link
    url = (s.get("source_url") or "").strip()
    if not url or url == "#" or not url.startswith("http"):
        continue
        
    # Dynamically validate and close scholarship if deadline has passed
    dl = s.get("deadline", "")
    if dl:
        match_dl = re.search(r"(\d{4})-(\d{2})-(\d{2})", dl)
        if match_dl:
            try:
                from datetime import datetime
                year, month, day = map(int, match_dl.groups())
                deadline_date = datetime(year, month, day).date()
                current_date = datetime.now().date()
                if deadline_date < current_date:
                    s["application_status"] = "closed"
            except Exception:
                pass
        
    # Country filter
    if filter_country != "Todos" and filter_country.lower() not in (s.get("country") or "").lower():
        continue
    
    # Academic level filter
    if filter_level != "Todos":
        raw_lvl = level_display_to_raw.get(filter_level)
        if raw_lvl and raw_lvl.lower() not in (s.get("academic_level") or "").lower():
            continue
            
    # Status filter
    status_val = (s.get("application_status") or "unknown").lower()
    if filter_status == "Abiertas" and "open" not in status_val:
        continue
    if filter_status == "Cerradas" and ("closed" in status_val or "expired" in status_val):
        continue
        
    # Deeper check: Analizar requisitos de ciudadanía/nacionalidad
    user_nat = _profile.get("nationality", "").strip().lower()
    
    def normalize_country(c):
        c = str(c).lower().strip()
        if "ecuator" in c or "ecuador" in c: return "ecuador"
        if "colomb" in c: return "colombia"
        if "venez" in c: return "venezuela"
        if "argent" in c: return "argentina"
        if "peru" in c: return "peru"
        if "chile" in c: return "chile"
        if "span" in c or "españ" in c: return "spain"
        if "german" in c or "alem" in c: return "germany"
        if "canad" in c: return "canada"
        if "american" in c or "united states" in c or "usa" in c: return "united states"
        return c

    user_nat_norm = normalize_country(user_nat) if user_nat else ""

    def pl_sub(v):
        if isinstance(v, list): return v
        try: return json.loads(v or "[]")
        except: return []

    eligible_nats = pl_sub(s.get("eligible_nationalities_json") or s.get("eligible_nationalities", []))
    reqs_list = pl_sub(s.get("requirements_json") or s.get("requirements", []))
    reqs_text = " ".join(reqs_list).lower()
    
    citizenship_incompatible = False
    
    if eligible_nats and user_nat_norm:
        has_match = False
        is_global = False
        for n in eligible_nats:
            n_norm = normalize_country(n)
            if n_norm in ("global", "all", "any", "todo el mundo", "todos", "abierto", ""):
                is_global = True
                break
            if user_nat_norm in n_norm or n_norm in user_nat_norm:
                has_match = True
                break
        if not is_global and not has_match:
            citizenship_incompatible = True
            
    # Check explicit citizen requirements in description/requirements text
    for other_country in ["germany", "alemania", "united states", "eeuu", "usa", "canada", "colombia", "spain", "españa"]:
        if other_country in reqs_text and other_country != user_nat_norm:
            if "citizen" in reqs_text or "ciudadan" in reqs_text:
                citizenship_incompatible = True

    if citizenship_incompatible:
        nats_filtered_count += 1
        continue

    # Text search keyword filter
    if filter_text:
        t_query = filter_text.lower()
        name = (s.get("scholarship_name") or "").lower()
        inst = (s.get("institution") or "").lower()
        reason = (s.get("relevance_reason") or "").lower()
            
        reqs_str = " ".join(reqs_list).lower()
        fields_str = " ".join(pl_sub(s.get("fields_json") or s.get("fields", []))).lower()
        benefits_str = " ".join(pl_sub(s.get("benefits_json") or s.get("benefits", []))).lower()
        
        if (t_query not in name and t_query not in inst and t_query not in reason and 
            t_query not in reqs_str and t_query not in fields_str and t_query not in benefits_str):
            continue
            
    filtered_tuples.append((idx, s))

# Apply sorting
if sort_option == "Por fecha límite (Más cercanas)":
    def get_dl_key(item):
        s = item[1]
        dl = s.get("deadline", "")
        if not dl:
            return "9999-12-31"
        match = re.search(r"\d{4}-\d{2}-\d{2}", dl)
        if match:
            return match.group()
        return dl
    filtered_tuples.sort(key=get_dl_key)
elif sort_option == "Alfabéticamente (A-Z)":
    filtered_tuples.sort(key=lambda item: (item[1].get("scholarship_name") or "").lower())
else:
    # Por relevancia (default original)
    filtered_tuples.sort(key=lambda item: item[0])

filtered_results = [item[1] for item in filtered_tuples]

if raw_results:
    st.markdown(f"**{len(filtered_results)} oportunidades encontradas (filtradas de {len(raw_results)})**")
    if nats_filtered_count > 0:
        st.markdown(
            f"<div style='background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.25);border-radius:8px;padding:0.5rem 0.8rem;color:#f87171;font-size:0.82rem;margin-bottom:1rem;'>"
            f"⚠️ <strong>Exclusiones del Perfil:</strong> {nats_filtered_count} {'oportunidad fue excluida' if nats_filtered_count == 1 else 'oportunidades fueron excluidas'} "
            f"automáticamente debido a requisitos de ciudadanía o nacionalidades incompatibles con tu perfil."
            f"</div>",
            unsafe_allow_html=True
        )
    st.markdown("---")
    
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

    def pl(v):
        if isinstance(v, list): return v
        try: return json.loads(v or "[]")
        except: return []

    for s in filtered_results:
        status_val = (s.get("application_status") or "unknown").lower()
        sc = "tag-open" if "open" in status_val else ("tag-closed" if status_val in ("closed","expired") else "tag-l")
        fields = "".join(f'<span class="tag tag-f">{f}</span>' for f in pl(s.get("fields_json") or s.get("fields",[]))[:4])
        reason_html = f'<div class="reason">✨ {s.get("relevance_reason","")}</div>' if s.get("relevance_reason") else ""
        url = s.get("source_url","")
        url_html = f'<a href="{url}" target="_blank" style="color:#9DFF00;font-size:.85rem;font-weight:600;text-decoration:none;margin-top:0.4rem;display:inline-block;">🔗 Ver portal oficial de postulación →</a>' if url else ""
        dl = s.get("deadline","")
        
        # Format the deadline badge
        dl_badge = f'<span class="tag tag-l" style="background:rgba(250,204,21,.15);color:#facc15;border:1px solid rgba(250,204,21,.3);">📅 {dl}</span>' if dl else ""
        
        card_html = (
            f'<div class="s-card">'
            f'<div class="s-title" style="color:#ffffff;font-size:1.2rem;margin-bottom:0.3rem;">{s.get("scholarship_name","—")}</div>'
            f'<div class="s-inst" style="color:#9DFF00;font-weight:500;margin-bottom:0.7rem;">{s.get("institution","")}</div>'
            f'<div><span class="tag tag-c">{get_country_flag(s.get("country","—"))}</span>'
            f'<span class="tag tag-l">🎓 {s.get("academic_level","—")}</span>'
            f'<span class="tag {sc}">● {status_val.upper()}</span>'
            f'{dl_badge}'
            f'{fields}</div>'
            f'{reason_html}'
            f'<div style="margin-top:0.8rem;text-align:right;">{url_html}</div>'
            f'</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)
        
        # --- Expandable details ---
        with st.expander("📋 Ver detalles de la convocatoria", expanded=False):
            col_det1, col_det2 = st.columns(2)
            with col_det1:
                st.markdown("##### 📅 Fechas clave")
                if dl:
                    st.markdown(f"<div style='font-size:1.05rem;color:#facc15;font-weight:600;margin-bottom:1rem;'>📅 Cierre de postulación: {dl}</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div style='font-size:0.95rem;color:#64748b;margin-bottom:1rem;'>📅 Cierre: No especificado / Convocatoria abierta</div>", unsafe_allow_html=True)
                
                st.markdown("##### 🌍 Elegibilidad y Requisitos")
                nats = pl(s.get("eligible_nationalities_json") or s.get("eligible_nationalities", []))
                if nats:
                    st.markdown(f"**Nacionalidades elegibles:** {', '.join(nats)}")
                else:
                    st.markdown("**Nacionalidades elegibles:** Abierto globalmente")
                    
                langs = pl(s.get("required_languages_json") or s.get("required_languages", []))
                if langs:
                    st.markdown(f"**Idiomas requeridos:** {', '.join(langs)}")
                else:
                    st.markdown("**Idiomas requeridos:** No especificados")
                    
                reqs = pl(s.get("requirements_json") or s.get("requirements", []))
                if reqs:
                    st.markdown("**Requisitos específicos:**")
                    for r in reqs:
                        st.markdown(f"- 🔸 {r}")
                else:
                    st.markdown("*No se listan requisitos específicos.*")
            
            with col_det2:
                st.markdown("##### 🎁 Beneficios")
                benefits = pl(s.get("benefits_json") or s.get("benefits", []))
                if benefits:
                    for b in benefits:
                        st.markdown(f"- ✅ {b}")
                else:
                    st.markdown("*No se listan beneficios específicos.*")
                
                snippets = pl(s.get("evidence_snippets_json") or s.get("evidence_snippets", []))
                if snippets:
                    st.markdown("##### 💬 Información del Portal Oficial")
                    for snip in snippets[:2]:
                        st.markdown(f"> *\"{snip}\"*")
                
                if url_html:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown(url_html, unsafe_allow_html=True)

        if _AUTH_AVAILABLE and user:
            if st.button(
                "📝 Preparar postulación",
                key=f"apply_{s.get('scholarship_hash', s.get('scholarship_name', ''))}",
            ):
                st.session_state["apply_scholarship"] = dict(s)
                st.switch_page("pages/3_Apply_Scholarship.py")
        st.markdown("<br>", unsafe_allow_html=True)

elif _quota_ok and _profile_ok:
    st.markdown(
        "<div style='text-align:center;padding:3rem;color:#475569;'>"
        "<div style='font-size:4rem;'>🔍</div>"
        "<div style='margin-top:1rem;font-size:1.1rem;'>"
        "Perfil listo — pulsa Search para encontrar becas acordes a tu perfil."
        "</div></div>",
        unsafe_allow_html=True,
    )
