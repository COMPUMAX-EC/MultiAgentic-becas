"""3_Apply_Scholarship.py — Asistente de postulación (campos + carta de intención)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

st.set_page_config(page_title="Apply to Scholarship", page_icon="📝", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
[data-testid="stAppViewContainer"]{background:linear-gradient(135deg,#0a0e1a,#0f172a,#1a1035);}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0d1321,#141b2d);border-right:1px solid #1e293b;}
.field-card{background:rgba(15,23,42,.85);border:1px solid rgba(99,102,241,.25);
    border-radius:12px;padding:1rem 1.2rem;margin-bottom:.8rem;}
</style>
""", unsafe_allow_html=True)

try:
    from auth.session import get_current_user, require_login
    from database.repository import get_user_profile, list_recent_scholarships
    from frontend.utils.auth_ui import render_auth_sidebar
    from frontend.utils.profile_ui import profile_is_complete, render_profile_editor
    from services.application_service import build_application_package, ApplicationAgentError

    _user = get_current_user()
except ImportError:
    st.error("Módulo de autenticación no disponible.")
    st.stop()

with st.sidebar:
    st.markdown("### 🎓 MultiAgentic\n**Scholarships**")
    st.markdown("---")
    st.page_link("app.py", label="🏠 Home")
    st.page_link("pages/1_Search_Scholarships.py", label="🔍 Search Scholarships")
    st.page_link("pages/3_Apply_Scholarship.py", label="📝 Apply to Scholarship")
    st.page_link("pages/2_Monitor.py", label="📊 System Monitor")
    st.markdown("---")
    render_auth_sidebar()

user = require_login(sidebar_only=True)

st.markdown("## 📝 Asistente de postulación")
st.caption(
    "Analiza el formulario de la beca, sugiere valores según tu perfil y redacta "
    "una carta de intención alineada. **No envía** el formulario por ti — revisa todo antes."
)

profile = render_profile_editor(user.sub)
if not profile_is_complete(profile):
    st.warning("Completa y guarda tu perfil académico antes de generar la postulación.")
    st.stop()

scholarships = list_recent_scholarships(limit=30)
preselected = st.session_state.pop("apply_scholarship", None)
scholarship_options: dict[str, dict] = {}
for s in scholarships:
    label = f"{s.get('scholarship_name', 'Sin nombre')} — {s.get('country', '')}"
    scholarship_options[label] = s

st.markdown("### 1. Selecciona la beca")
col_a, col_b = st.columns([1, 1])
default_index = 0
if preselected:
    for i, label in enumerate(scholarship_options.keys()):
        if scholarship_options[label].get("scholarship_name") == preselected.get(
            "scholarship_name"
        ):
            default_index = i + 1
            break

with col_a:
    pick = st.selectbox(
        "Beca en base de conocimiento",
        ["— Manual —"] + list(scholarship_options.keys()),
        index=default_index,
        label_visibility="collapsed",
    )
with col_b:
    custom_url = st.text_input(
        "URL del formulario de postulación (opcional)",
        placeholder="https://...",
    )

selected: dict = {}
if pick != "— Manual —" and pick in scholarship_options:
    selected = scholarship_options[pick]
else:
    selected = {
        "scholarship_name": st.text_input("Nombre de la beca", ""),
        "institution": st.text_input("Institución", ""),
        "country": st.text_input("País", ""),
        "academic_level": profile.get("academic_level", ""),
        "field_of_study": profile.get("field_of_study", ""),
        "requirements": st.text_area("Requisitos conocidos", height=80),
        "application_url": custom_url,
    }

if not selected.get("scholarship_name"):
    st.info("Elige una beca de la lista o escribe el nombre manualmente.")
    st.stop()

if custom_url.strip():
    selected["application_url"] = custom_url.strip()

st.markdown("### 2. Generar borrador de postulación")
if st.button("🚀 Preparar postulación", type="primary"):
    with st.spinner("Analizando formulario y redactando contenido…"):
        try:
            pkg = build_application_package(
                profile=profile,
                scholarship=selected,
                applicant_name=user.name,
                applicant_email=user.email,
                application_url=selected.get("application_url") or custom_url or None,
            )
            st.session_state["last_application_pkg"] = pkg
        except ApplicationAgentError as exc:
            st.error(str(exc))

pkg = st.session_state.get("last_application_pkg")
if not pkg:
    st.markdown(
        "<div style='text-align:center;padding:2rem;color:#475569;'>"
        "Pulsa <strong>Preparar postulación</strong> para obtener campos y carta."
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()

st.success("Borrador listo — revisa cada campo antes de enviar en el portal oficial.")

if pkg.get("application_url"):
    st.link_button("🔗 Abrir portal de postulación", pkg["application_url"])

analysis = pkg.get("analysis", {})
st.markdown("#### Propósito de la beca (para alinear la carta)")
st.write(analysis.get("scholarship_purpose", "—"))

if analysis.get("requires_letter_of_intent"):
    st.markdown(
        f"📄 **Carta requerida:** {analysis.get('letter_type', 'motivation')} "
        f"({analysis.get('letter_language', 'es')})"
    )

st.markdown("### 3. Campos del formulario")
for field in pkg.get("filled_fields", []):
    conf = field.get("confidence", 0)
    color = "#4ade80" if conf >= 75 else ("#facc15" if conf >= 50 else "#f87171")
    with st.expander(f"{field.get('label')} — confianza {conf}%", expanded=conf < 75):
        st.markdown(
            f"<span style='color:{color};font-size:.75rem;'>Sugerencia automática</span>",
            unsafe_allow_html=True,
        )
        st.text_area(
            "Valor",
            value=field.get("suggested_value", ""),
            height=100,
            key=f"field_{field.get('field_id')}",
            label_visibility="collapsed",
        )
        if field.get("notes"):
            st.caption(field["notes"])

letter = pkg.get("letter_of_intent")
if letter:
    st.markdown("### 4. Carta de intención / motivación")
    st.text_area("Carta", value=letter, height=320, label_visibility="collapsed")

st.markdown("### Checklist")
for item in pkg.get("submission_checklist", []):
    st.markdown(f"- {item}")

for warn in pkg.get("warnings", []):
    st.warning(warn)

from frontend.utils.application_export import package_to_markdown

md = package_to_markdown(pkg)
st.download_button(
    "⬇️ Descargar borrador (.md)",
    data=md,
    file_name="postulacion_beca.md",
    mime="text/markdown",
)
with st.expander("Ver JSON completo"):
    st.json(pkg)
