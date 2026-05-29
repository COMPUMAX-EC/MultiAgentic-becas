"""3_Apply_Scholarship.py — Asistente de postulación (campos + carta de intención)."""
from __future__ import annotations

import json, re
import sys
from pathlib import Path

# Force the correct project root at position 0 of sys.path
_PROJECT_ROOT = Path("/home/squelal91/MultiAgentic-becas")
if str(_PROJECT_ROOT) in sys.path:
    sys.path.remove(str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT))

# Clean up cached modules under 'utils' namespace to prevent Streamlit folder conflict
for k in list(sys.modules.keys()):
    if k == "utils" or k.startswith("utils."):
        sys.modules.pop(k, None)

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

st.set_page_config(page_title="Apply to Scholarship", page_icon="📝", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
[data-testid="stAppViewContainer"]{background:linear-gradient(135deg,#050505,#1a1a1a,#050505);}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#050505,#1a1a1a);border-right:1px solid rgba(157,255,0,0.35);}
[data-testid="stSidebarNav"]{display:none !important;}
[data-testid="stHeader"] {
    background: transparent !important;
    color: transparent !important;
    pointer-events: none !important;
}
[data-testid="stHeader"] [data-testid="stHeaderActionElements"] {
    display: none !important;
}
button[data-testid="stExpandSidebarButton"] {
    pointer-events: auto !important;
    color: #9DFF00 !important;
    background-color: rgba(26, 26, 26, 0.8) !important;
    border: 1px solid rgba(157, 255, 0, 0.3) !important;
    border-radius: 8px !important;
    margin-left: 10px !important;
    margin-top: 10px !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
}
button[data-testid="stExpandSidebarButton"] * {
    color: #9DFF00 !important;
    fill: #9DFF00 !important;
}
[data-testid="stToolbar"]{display:none !important;}
footer{visibility:hidden !important;}
.block-container, .stMainBlockContainer {
    padding-top: 1.5rem !important;
    padding-bottom: 1rem !important;
}
.field-card{background:#1A1A1A;border:1px solid rgba(157,255,0,0.25);
    border-radius:12px;padding:1rem 1.2rem;margin-bottom:.8rem;}
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

try:
    from auth.session import get_current_user, require_login
    from database.repository import get_user_profile, list_recent_scholarships, get_user, update_user_premium_status
    from frontend.utils.auth_ui import render_auth_sidebar
    from frontend.utils.profile_ui import profile_is_complete, render_profile_editor
    from services.application_service import build_application_package, ApplicationAgentError

except Exception as e:
    try:
        import traceback
        with open("/home/squelal91/MultiAgentic-becas/api.log", "a") as f:
            f.write(f"\n--- ERROR EN 3_Apply_Scholarship.py ---\n")
            f.write(traceback.format_exc())
            f.write("\n---------------------------------------\n")
    except Exception:
        pass
    st.error(f"Error de inicialización: {e}")
    st.exception(e)
    st.stop()

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
    render_auth_sidebar()

user = require_login(sidebar_only=True)

# Initialize applied scholarships session state
if "applied_scholarships" not in st.session_state:
    st.session_state["applied_scholarships"] = []

# Render premium top header
try:
    from frontend.utils.header_ui import render_custom_header
    render_custom_header()
except Exception:
    pass

st.markdown("## 📝 Asistente de postulación")
st.caption(
    "Analiza el formulario de la beca, sugiere valores según tu perfil y redacta "
    "una carta de intención alineada. **No envía** el formulario por ti — revisa todo antes."
)

profile = render_profile_editor(user.sub)
if not profile_is_complete(profile):
    st.warning("Completa y guarda tu perfil académico antes de generar la postulación.")
    st.stop()

# Initialize session state for premium
db_user = get_user(user.sub) if user else {}
db_premium_status = db_user.get("premium_status", "none") if db_user else "none"
db_is_premium = (db_user.get("is_premium") == 1) if db_user else False

st.session_state["is_premium"] = db_is_premium

st.markdown("---")
st.markdown("### 💎 Configuración de Modo de Postulación")

# Load suitable scholarships compatible with the profile
all_scholarships = list_recent_scholarships(limit=50)
user_level = profile.get("academic_level", "").lower().strip()
matching_scholarships = []
for s in all_scholarships:
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
    # Validar que la beca esté abierta
    status_val = (s.get("application_status") or "").lower()
    if "open" not in status_val:
        continue
    s_lvl = (s.get("academic_level") or "").lower().strip()
    if user_level in s_lvl or s_lvl in user_level or not s_lvl:
        matching_scholarships.append(s)

if not st.session_state.get("is_premium", False):
    premium_cols = st.columns([1, 1])
    with premium_cols[0]:
        st.markdown("""
        <div style="background:rgba(157,255,0,0.06);border:1px solid rgba(157,255,0,0.25);border-radius:12px;padding:0.8rem 1.2rem;margin-bottom:0.8rem;">
            <span style="color:#9DFF00;font-weight:600;font-size:1.05rem;">⚡ Modo Premium — Postulación Automática Masiva</span><br>
            <span style="font-size:0.82rem;color:#94a3b8;">
                Escanea el QR de pago directo DevIALabs de abajo y sube el comprobante de tu transferencia ($4.99 USD) para desbloquear la IA inteligente que postulará a todas las becas de tu perfil de forma automática.
            </span>
        </div>
        """, unsafe_allow_html=True)
        
        if db_premium_status == "none":
            st.image("qr.jpg", caption="QR de Pago Directo - DevIALabs", width=250)
            receipt = st.file_uploader(
                "Subir comprobante de transferencia directa (.pdf, .png, .jpg)",
                type=["pdf", "png", "jpg", "jpeg"],
                key="premium_receipt_uploader_field"
            )
            if receipt is not None:
                # Save file physically to data/receipts/
                receipts_dir = Path(_PROJECT_ROOT) / "data" / "receipts"
                receipts_dir.mkdir(parents=True, exist_ok=True)
                
                # Use a safe unique filename
                import re
                safe_filename = f"receipt_{user.sub}_{receipt.name}"
                safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', safe_filename)
                
                file_path = receipts_dir / safe_filename
                with open(file_path, "wb") as f:
                    f.write(receipt.read())
                    
                # Update database status
                update_user_premium_status(user.sub, "pending_approval", receipt_path=str(file_path))
                st.rerun()
        else:
            if db_premium_status == "pending_approval":
                st.markdown("""
                <div style="background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);border-radius:12px;padding:1rem 1.2rem;margin-bottom:0.8rem;">
                    <span style="color:#f59e0b;font-weight:600;font-size:1.05rem;">⏳ Validación en Progreso (10 Minutos)</span><br>
                    <span style="font-size:0.82rem;color:#e2e8f0;display:inline-block;margin-top:0.3rem;">
                        Tu comprobante de pago ha sido cargado con éxito. La validación manual de tu transferencia directa en <strong>DevIALabs</strong> tomará aproximadamente <strong>10 minutos</strong>. Se te notificará de inmediato.
                    </span>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🔄 Cambiar comprobante"):
                        update_user_premium_status(user.sub, "none")
                        st.rerun()
                with c2:
                    if st.button("⚡ Simular Validación (Pruebas)"):
                        update_user_premium_status(user.sub, "approved")
                        st.rerun()
            elif db_premium_status == "rejected":
                st.markdown("""
                <div style="background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.3);border-radius:12px;padding:1rem 1.2rem;margin-bottom:0.8rem;">
                    <span style="color:#ef4444;font-weight:600;font-size:1.05rem;">❌ Transferencia Rechazada</span><br>
                    <span style="font-size:0.82rem;color:#e2e8f0;display:inline-block;margin-top:0.3rem;">
                        Lo sentimos, tu comprobante de pago no pudo ser validado. Por favor, asegúrate de que los datos de la transferencia de <strong>$4.99 USD</strong> sean correctos y sube un nuevo comprobante válido.
                    </span>
                </div>
                """, unsafe_allow_html=True)
                if st.button("🔄 Subir nuevo comprobante"):
                    update_user_premium_status(user.sub, "none")
                    st.rerun()

    with premium_cols[1]:
        st.markdown("### 🔒 Vista Previa de Oportunidades")
        st.caption("Estas son las becas en la base de conocimiento compatibles con tu perfil académico. Activa tu cuenta Premium para iniciar el proceso de postulación automática.")
        
        if not matching_scholarships:
            st.info("No se encontraron becas en la base de datos que coincidan exactamente con tu nivel académico actual.")
        else:
            st.write(f"**Oportunidades encontradas compatibles con tu perfil ({len(matching_scholarships)}):**")
            for s in matching_scholarships:
                status_val = (s.get("application_status") or "unknown").lower()
                sc = "tag-open" if "open" in status_val else ("tag-closed" if status_val in ("closed","expired") else "tag-l")
                st.markdown(f"""
                <div style="background:#1A1A1A;border:1px solid rgba(255,255,255,0.05);border-radius:10px;padding:0.6rem 1rem;margin-bottom:0.5rem;display:flex;justify-content:space-between;align-items:center;opacity:0.65;">
                    <div>
                        <div style="color:#ffffff;font-size:0.9rem;font-weight:600;">🔒 {s.get('scholarship_name')}</div>
                        <div style="color:#9DFF00;font-size:0.75rem;font-weight:500;">🏫 {s.get('institution')} | 🌍 {s.get('country')}</div>
                    </div>
                    <span class="tag {sc}" style="margin:0;">● {status_val.upper()}</span>
                </div>
                """, unsafe_allow_html=True)
else:
    # User is PREMIUM: Full width Auto-Apply Page!
    st.markdown("""
    <div style="background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.3);border-radius:10px;padding:0.6rem 1rem;color:#4ade80;font-size:0.85rem;font-weight:600;margin-bottom:1.5rem;">
        💎 PRO Status Activo — ¡Disfruta de las postulaciones automáticas masivas con inteligencia artificial!
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### ⚡ Aplicación Automática Premium")
    st.caption("El agente inteligente de DevIALabs evaluará y preparará tu postulación para todas las becas en base de conocimiento que coincidan con tu nivel académico.")
    
    if not matching_scholarships:
        st.warning("No se encontraron becas en la base de datos que coincidan exactamente con tu nivel académico actual.")
    else:
        st.write("---")
        st.markdown("#### ⚙️ Configuración de Aplicación Automática")
        
        # Mode Selection inside Auto-Apply Mode
        selection_mode = st.radio(
            "Selecciona tu preferencia de aplicación automática:",
            [
                "⚡ Aplicar automáticamente a TODAS las becas acordes al perfil (Por defecto)",
                "🔍 Seleccionar manualmente cuáles becas aplicar"
            ],
            index=0,
            key="premium_auto_apply_selection"
        )
        
        target_scholarships = []
        if selection_mode == "🔍 Seleccionar manualmente cuáles becas aplicar":
            st.write("**Selecciona las becas a las que deseas aplicar:**")
            for idx, s in enumerate(matching_scholarships):
                # Render checkbox for each matching scholarship
                chk_label = f"🎓 {s.get('scholarship_name')} — 🏫 {s.get('institution')} ({s.get('country')})"
                is_selected = st.checkbox(
                    label=chk_label,
                    value=True,  # Default to checked/active
                    key=f"check_scholarship_{idx}"
                )
                if is_selected:
                    target_scholarships.append(s)
        else:
            target_scholarships = matching_scholarships
            
        if not target_scholarships:
            st.warning("⚠️ Debes seleccionar al menos una beca para iniciar el proceso de postulación automática.")
        else:
            if selection_mode != "🔍 Seleccionar manualmente cuáles becas aplicar":
                st.write(f"**Becas listas para postulación automática ({len(target_scholarships)}):**")
                # Display list
                for s in target_scholarships:
                    status_val = (s.get("application_status") or "unknown").lower()
                    sc = "tag-open" if "open" in status_val else ("tag-closed" if status_val in ("closed","expired") else "tag-l")
                    
                    st.markdown(f"""
                    <div style="background:#1A1A1A;border:1px solid rgba(157,255,0,0.15);border-radius:10px;padding:0.6rem 1rem;margin-bottom:0.5rem;display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <span style="color:#ffffff;font-size:0.9rem;font-weight:600;">🎓 {s.get('scholarship_name')}</span><br>
                            <span style="color:#9DFF00;font-size:0.75rem;font-weight:500;">🏫 {s.get('institution')} | 🌍 {s.get('country')}</span>
                        </div>
                        <span class="tag {sc}" style="margin:0;">● {status_val.upper()}</span>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.write("") # Spacer
            
            if st.button("🚀 Iniciar Postulación Masiva Automática", type="primary", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                applied = st.session_state.get("applied_scholarships", [])
                from datetime import datetime
                from application.auto_apply_agent import AutoApplyAgent
                from services.application_service import build_application_package
                import time
                
                for idx, s in enumerate(target_scholarships):
                    percent = int(((idx + 1) / len(target_scholarships)) * 100)
                    s_name = s.get("scholarship_name") or s.get("name") or "Beca"
                    status_text.markdown(f"🤖 **AutoApply Agent**: Analizando y preparando postulación para *{s_name}*...")
                    progress_bar.progress(percent)
                    
                    try:
                        # 1. Run actual ApplicationAgent to extract form context & draft letter
                        package_result = build_application_package(
                            profile=profile,
                            scholarship=s,
                            applicant_name=user.name if user and user.name else "Estudiante",
                            applicant_email=user.email if user and user.email else "",
                        )
                        
                        # 2. Run AutoApplyAgent to generate Word file (.docx) and Autofill (.json)
                        auto_apply_agent = AutoApplyAgent()
                        files_result = auto_apply_agent.generate_postulation_package(
                            profile=profile,
                            scholarship=s,
                            package=package_result,
                            user_sub=user.sub if user else "guest",
                        )
                        
                        # 3. Add to applied list if not already there (or replace if existing to update)
                        applied = [a for a in applied if a.get("scholarship_name") != s_name]
                        
                        applied.append({
                            "scholarship_name": s_name,
                            "institution": s.get("institution") or "—",
                            "country": s.get("country") or "—",
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "docx_path": files_result["docx_path"],
                            "docx_filename": files_result["docx_filename"],
                            "json_path": files_result["json_path"],
                            "json_filename": files_result["json_filename"],
                            "letter_content": package_result.get("letter_of_intent", ""),
                            "checklist": package_result.get("submission_checklist", []),
                            "fields": package_result.get("filled_fields", []),
                        })
                    except Exception as e:
                        # Fallback basic mapping
                        applied = [a for a in applied if a.get("scholarship_name") != s_name]
                        applied.append({
                            "scholarship_name": s_name,
                            "institution": s.get("institution") or "—",
                            "country": s.get("country") or "—",
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "error": str(e)
                        })
                        
                st.session_state["applied_scholarships"] = applied
                status_text.success(f"🎉 ¡Postulación Masiva Completada! Se han preparado borradores de postulación automática para las {len(target_scholarships)} becas seleccionadas. Revisa tu panel abajo 💎.")
                progress_bar.progress(100)
                time.sleep(1.5)
                st.rerun()

    # ── Applied Scholarships Dashboard ──
    applied = st.session_state.get("applied_scholarships", [])
    if applied:
        st.markdown("---")
        st.markdown("### 📋 Tus Postulaciones Preparadas (Modo Premium)")
        st.caption("A continuación encontrarás tus paquetes de postulación generados de forma inteligente. Puedes descargar tu carta de intención/motivación en formato Word (.docx) profesional y tu payload de auto-rellenado (.json) para la automatización.")
        
        for idx, app in enumerate(reversed(applied)):
            s_name = app.get("scholarship_name")
            inst = app.get("institution") or "—"
            country = app.get("country") or "—"
            date_str = app.get("date")
            
            with st.container():
                st.markdown(f"""
                <div style="background:#1A1A1A;border:1px solid rgba(157,255,0,0.25);border-radius:12px;padding:1rem 1.2rem;margin-bottom:1rem;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
                        <div>
                            <span style="color:#ffffff;font-size:1.1rem;font-weight:600;">🎓 {s_name}</span><br>
                            <span style="color:#9DFF00;font-size:0.8rem;">🏫 {inst} | 🌍 {country}</span>
                        </div>
                        <span style="font-size:0.75rem;color:#64748b;font-family:'JetBrains Mono',monospace;">📅 {date_str}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if app.get("error"):
                    st.error(f"Error al procesar esta postulación: {app.get('error')}")
                    continue
                    
                # Download buttons
                btn_col1, btn_col2 = st.columns(2)
                
                # Load DOCX bytes
                docx_path = app.get("docx_path")
                docx_filename = app.get("docx_filename")
                if docx_path and Path(docx_path).exists():
                    with open(docx_path, "rb") as f:
                        docx_bytes = f.read()
                    with btn_col1:
                        st.download_button(
                            label="📄 Descargar Carta de Motivación (.docx)",
                            data=docx_bytes,
                            file_name=docx_filename,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"dl_docx_{idx}"
                        )
                        
                # Load JSON bytes
                json_path = app.get("json_path")
                json_filename = app.get("json_filename")
                if json_path and Path(json_path).exists():
                    with open(json_path, "rb") as f:
                        json_bytes = f.read()
                    with btn_col2:
                        st.download_button(
                            label="⚙️ Descargar Payload de Auto-rellenado (.json)",
                            data=json_bytes,
                            file_name=json_filename,
                            mime="application/json",
                            key=f"dl_json_{idx}"
                        )
                
                # Preview expander
                with st.expander("👁️ Ver Borrador de Carta de Motivación y Detalles", expanded=False):
                    tab_letter, tab_fields = st.tabs(["📝 Carta de Motivación", "📋 Campos Auto-rellenados"])
                    with tab_letter:
                        st.markdown("**Borrador de Carta Generado:**")
                        st.text_area("Vista previa", value=app.get("letter_content", ""), height=300, disabled=True, key=f"preview_letter_{idx}")
                    with tab_fields:
                        st.markdown("**Campos de formulario sugeridos por el agente:**")
                        for field in app.get("fields", []):
                            fid = field.get("field_id")
                            lbl = field.get("label") or fid
                            val = field.get("suggested_value") or "—"
                            notes = field.get("notes") or ""
                            notes_str = f" (*{notes}*)" if notes else ""
                            st.markdown(f"- **{lbl}**: `{val}`{notes_str}")
                        
                        checklist = app.get("checklist", [])
                        if checklist:
                            st.markdown("**Lista de verificación para postulación:**")
                            for item in checklist:
                                st.markdown(f"- [ ] {item}")
                st.markdown("<br>", unsafe_allow_html=True)

