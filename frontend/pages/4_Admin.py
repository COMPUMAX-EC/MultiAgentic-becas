"""4_Admin.py — Administrative Control Panel for DevIALabs platform."""
from __future__ import annotations

import json
import os
import re
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

st.set_page_config(page_title="Panel de Administración", page_icon="⚙️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
[data-testid="stAppViewContainer"]{background:linear-gradient(135deg,#050505,#111111,#050505);}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#050505,#111111);border-right:1px solid rgba(157,255,0,0.35);}
[data-testid="stSidebarNav"]{display:none !important;}
[data-testid="stHeader"]{display:none !important;}
[data-testid="stToolbar"]{display:none !important;}
footer{visibility:hidden !important;}

/* Admin Custom styling */
.admin-title {
    font-size: 2.2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #9DFF00, #FFFFFF, #9DFF00);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.2rem;
}
.glass-card {
    background: rgba(26, 26, 26, 0.7);
    border: 1px solid rgba(157, 255, 0, 0.15);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(8px);
}
.stat-box {
    text-align: center;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}
.stat-box:last-child {
    border-right: none;
}
.stat-val {
    font-size: 2rem;
    font-weight: 700;
    color: #9DFF00;
}
.stat-lbl {
    font-size: 0.8rem;
    color: #94a3b8;
    margin-top: 0.2rem;
}

/* User approval rows */
.user-row {
    background: #1A1A1A;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 0.8rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: all 0.25s ease;
}
.user-row:hover {
    border-color: rgba(157, 255, 0, 0.25);
    box-shadow: 0 4px 20px rgba(157, 255, 0, 0.08);
}
.user-details {
    display: flex;
    align-items: center;
    gap: 1rem;
}
.user-avatar {
    width: 46px;
    height: 46px;
    border-radius: 50%;
    border: 2px solid #9DFF00;
    object-fit: cover;
}
.user-default-avatar {
    width: 46px;
    height: 46px;
    border-radius: 50%;
    border: 2px solid #9DFF00;
    background: rgba(157, 255, 0, 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
}
.user-name-text {
    font-size: 1.05rem;
    font-weight: 600;
    color: #FFFFFF;
}
.user-email-text {
    font-size: 0.82rem;
    color: #94a3b8;
}

/* Area cards */
.area-card {
    background: #1A1A1A;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 1.2rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.25s ease;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.area-card:hover {
    border-color: #9DFF00;
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(157, 255, 0, 0.12);
}
.area-icon {
    font-size: 2.2rem;
    margin-bottom: 0.4rem;
}
.area-name {
    font-size: 1.05rem;
    font-weight: 600;
    color: #E2E8F0;
}
.area-count {
    font-size: 0.8rem;
    color: #9DFF00;
    font-weight: 500;
    margin-top: 0.3rem;
}

/* Base custom scholarship card inside Admin */
.adm-s-card {
    background: rgba(26, 26, 26, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 1.2rem;
    margin-bottom: 0.8rem;
}
.adm-s-card:hover {
    border-color: rgba(157, 255, 0, 0.2);
}
.adm-s-title {
    font-size: 1.15rem;
    font-weight: 600;
    color: #FFFFFF;
}
.adm-s-inst {
    font-size: 0.85rem;
    color: #9DFF00;
    font-weight: 500;
    margin-bottom: 0.5rem;
}
.tag {
    display: inline-block;
    padding: .2rem .7rem;
    border-radius: 20px;
    font-size: .75rem;
    font-weight: 500;
    margin: .15rem;
}
.tag-c {
    background: rgba(157,255,0,0.15);
    color: #9DFF00;
    border: 1px solid rgba(157,255,0,0.3);
}
.tag-l {
    background: rgba(99,102,241,.15);
    color: #818cf8;
    border: 1px solid rgba(99,102,241,.3);
}
.tag-open {
    background: rgba(34,197,94,.15);
    color: #4ade80;
    border: 1px solid rgba(34,197,94,.3);
}
.tag-closed {
    background: rgba(239,68,68,.15);
    color: #f87171;
    border: 1px solid rgba(239,68,68,.3);
}

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
    try:
        from frontend.utils.auth_ui import render_auth_sidebar
        render_auth_sidebar()
    except Exception:
        pass

# ── Security Gating ──────────────────────────────────────────────────────────
try:
    from auth.session import require_login, is_admin_user
    from database.repository import get_user, update_user_premium_status, list_users_by_premium_status, list_all_scholarships
    
    user = require_login(sidebar_only=True)
    db_user = get_user(user.sub) if user else None
except Exception as e:
    st.error(f"Error de sistema al validar autenticación: {e}")
    st.stop()

# Ensure role is admin
if not is_admin_user(user):
    st.markdown(f"""
<div style="text-align:center;padding:5rem 2rem;color:#ef4444;">
    <div style="font-size:5rem;margin-bottom:1.5rem;">⛔</div>
    <h2 style="font-weight:700;margin-bottom:0.8rem;">Acceso Denegado</h2>
    <p style="color:#94a3b8;max-width:550px;margin:0 auto;line-height:1.5;font-size:0.95rem;">
        Lo sentimos, esta sección es exclusiva para administradores de la plataforma <strong>DevIALabs</strong>. 
        Inicia sesión con una cuenta con rol 'admin' o solicita permisos adicionales para ingresar.
    </p>
</div>
""", unsafe_allow_html=True)
    st.stop()

# ── Render Header ────────────────────────────────────────────────────────────
try:
    from frontend.utils.header_ui import render_custom_header
    render_custom_header()
except Exception:
    pass

st.markdown("<div class='admin-title'>⚙️ Panel de Administración</div>", unsafe_allow_html=True)
st.caption("Consola administrativa premium para gestionar membresías de usuarios y auditar el catálogo inteligente de becas.")

st.markdown("---")

# ── Quick Statistics Banner ──────────────────────────────────────────────────
all_users = list_users_by_premium_status()
pending_users = [u for u in all_users if u.get("premium_status") == "pending_approval"]
approved_users = [u for u in all_users if u.get("premium_status") == "approved"]
scholarships = list_all_scholarships()

s_col1, s_col2, s_col3, s_col4 = st.columns(4)
with s_col1:
    st.markdown(f"""<div class="glass-card stat-box">
        <div class="stat-val">{len(all_users)}</div><div class="stat-lbl">Usuarios Registrados</div>
    </div>""", unsafe_allow_html=True)
with s_col2:
    st.markdown(f"""<div class="glass-card stat-box">
        <div class="stat-val" style="color:#f59e0b;">{len(pending_users)}</div><div class="stat-lbl">Pendientes de Aprobación</div>
    </div>""", unsafe_allow_html=True)
with s_col3:
    st.markdown(f"""<div class="glass-card stat-box">
        <div class="stat-val" style="color:#4ade80;">{len(approved_users)}</div><div class="stat-lbl">Cuentas Premium Activas</div>
    </div>""", unsafe_allow_html=True)
with s_col4:
    st.markdown(f"""<div class="glass-card stat-box">
        <div class="stat-val">{len(scholarships)}</div><div class="stat-lbl">Becas Indexadas</div>
    </div>""", unsafe_allow_html=True)

# ── Admin Tabs ───────────────────────────────────────────────────────────────
admin_tabs = st.tabs(["💎 Aprobaciones Premium", "🎓 Becas por Área del Conocimiento"])

# ── TAB 1: Premium Approvals ────────────────────────────────────────────────
with admin_tabs[0]:
    st.markdown("### 💎 Control de Membresías Premium")
    st.caption("Valida las transferencias manuales realizadas por los usuarios y activa su cuenta de manera permanente.")
    
    # Filter selection
    filter_status = st.radio(
        "Filtrar solicitudes:",
        ["⏳ Pendientes de Validación", "✅ Aprobadas (Premium)", "❌ Rechazadas / Inactivas"],
        horizontal=True
    )
    
    db_filter = "pending_approval"
    if "Aprobadas" in filter_status:
        db_filter = "approved"
    elif "Rechazadas" in filter_status:
        db_filter = "rejected"
        
    filtered_users = list_users_by_premium_status(db_filter)
    
    if not filtered_users:
        st.info(f"No se encontraron solicitudes en estado: **{filter_status}**.")
    else:
        st.markdown("<br>", unsafe_allow_html=True)
        for idx, u_row in enumerate(filtered_users):
            u_sub = u_row.get("google_sub")
            u_name = u_row.get("name") or "Invitado"
            u_email = u_row.get("email") or "—"
            u_picture = u_row.get("picture_url")
            u_receipt = u_row.get("premium_receipt_path")
            
            avatar_html = f'<img src="{u_picture}" class="user-avatar">' if u_picture else '<div class="user-default-avatar">👤</div>'
            
            # Row render
            st.markdown(f"""
            <div class="user-row">
                <div class="user-details">
                    {avatar_html}
                    <div>
                        <span class="user-name-text">{u_name}</span><br>
                        <span class="user-email-text">✉️ {u_email} &nbsp;|&nbsp; Google ID: <code>{u_sub}</code></span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Details and actions columns
            action_cols = st.columns([2, 1, 1, 1])
            
            with action_cols[0]:
                if u_receipt and os.path.exists(u_receipt):
                    with open(u_receipt, "rb") as file_bytes:
                        st.download_button(
                            label="📄 Descargar Comprobante",
                            data=file_bytes,
                            file_name=os.path.basename(u_receipt),
                            mime="application/octet-stream",
                            key=f"dl_{u_sub}_{idx}"
                        )
                else:
                    st.caption("⚠️ No hay comprobante cargado en el servidor para este registro.")
                    
            with action_cols[1]:
                if db_filter != "approved":
                    if st.button("🟢 Aprobar", key=f"ap_{u_sub}_{idx}", use_container_width=True):
                        update_user_premium_status(u_sub, "approved")
                        st.success(f"¡Se ha activado el Modo Premium para {u_name}!")
                        st.rerun()
                else:
                    st.caption("✓ Premium Activo")
                    
            with action_cols[2]:
                if db_filter != "rejected":
                    if st.button("🔴 Rechazar", key=f"re_{u_sub}_{idx}", use_container_width=True):
                        update_user_premium_status(u_sub, "rejected")
                        st.warning(f"Se ha rechazado la solicitud de membresía para {u_name}.")
                        st.rerun()
                else:
                    st.caption("✓ Rechazado")
            
            with action_cols[3]:
                if db_filter != "none":
                    if st.button("🔄 Resetear", key=f"rs_{u_sub}_{idx}", use_container_width=True):
                        update_user_premium_status(u_sub, "none")
                        st.info(f"Se ha reiniciado el estado para {u_name}.")
                        st.rerun()
                        
            st.markdown("---")

# ── TAB 2: Scholarships by Area of Knowledge ───────────────────────────────
with admin_tabs[1]:
    st.markdown("### 🎓 Catálogo de Becas Académicas")
    st.caption("Audita la distribución y calidad del conocimiento recopilado automáticamente de la web.")
    
    # Process areas of knowledge dynamically
    # fields_json typically is a JSON string of a list: '["Engineering", "Arts"]'
    grouped_scholarships = {}
    for s in scholarships:
        fields_str = s.get("fields_json") or "[]"
        try:
            fields = json.loads(fields_str)
        except Exception:
            fields = []
        if not isinstance(fields, list):
            fields = [fields] if fields else []
        if not fields:
            fields = ["Sin clasificar / General"]
            
        for f in fields:
            f = str(f).strip().title()
            if not f:
                f = "Sin clasificar / General"
            if f not in grouped_scholarships:
                grouped_scholarships[f] = []
            grouped_scholarships[f].append(s)
            
    # Sorted areas list
    sorted_areas = sorted(list(grouped_scholarships.keys()), key=lambda x: len(grouped_scholarships[x]), reverse=True)
    
    # Render attractive Cards for areas using streamlit columns
    st.markdown("#### 📊 Distribución de Becas por Área")
    
    # Setup interactive filter
    selected_area = st.selectbox(
        "Selecciona un Área del Conocimiento para auditar las convocatorias:",
        ["Selecciona una opción..."] + sorted_areas
    )
    
    # Render general grid cards for quick view
    if selected_area == "Selecciona una opción...":
        st.markdown("<br>", unsafe_allow_html=True)
        area_cols = st.columns(4)
        
        # We define a few attractive icons for typical scholarship areas
        def get_area_icon(name: str) -> str:
            n = name.lower()
            if "ingenier" in n or "engineering" in n or "stem" in n or "tecnolog" in n or "science" in n:
                return "💻"
            if "medic" in n or "health" in n or "salud" in n or "biolog" in n:
                return "🩺"
            if "art" in n or "human" in n or "literat" in n or "music" in n:
                return "🎨"
            if "negoc" in n or "busin" in n or "admin" in n or "econom" in n:
                return "📈"
            if "socia" in n or "derech" in n or "law" in n or "politic" in n:
                return "⚖️"
            if "educac" in n or "teach" in n:
                return "🍎"
            return "🎓"
            
        for i, area in enumerate(sorted_areas):
            col_idx = i % 4
            with area_cols[col_idx]:
                count = len(grouped_scholarships[area])
                icon = get_area_icon(area)
                st.markdown(f"""
                <div class="area-card">
                    <div class="area-icon">{icon}</div>
                    <div class="area-name">{area}</div>
                    <div class="area-count">{count} convocatorias</div>
                </div>
                <br>
                """, unsafe_allow_html=True)
    else:
        # Render lists of scholarships inside the selected area
        s_list = grouped_scholarships.get(selected_area, [])
        st.markdown(f"#### 🎓 Convocatorias encontradas en **{selected_area}** ({len(s_list)})")
        st.write("---")
        
        def pl(v):
            if isinstance(v, list): return v
            try: return json.loads(v or "[]")
            except: return []
            
        for s in s_list:
            status_val = (s.get("application_status") or "unknown").lower()
            sc = "tag-open" if "open" in status_val else ("tag-closed" if status_val in ("closed","expired") else "tag-l")
            
            # Country with Flag
            country = s.get('country','—')
            flag_mapping = {
                "ecuador": "🇪🇨", "colombia": "🇨🇴", "peru": "🇵🇪", "venezuela": "🇻🇪",
                "argentina": "🇦🇷", "chile": "🇨🇱", "canada": "🇨🇦", "germany": "🇩🇪",
                "spain": "🇪🇸", "united kingdom": "🇬🇧", "uk": "🇬🇧", "france": "🇫🇷",
                "united states": "🇺🇸", "usa": "🇺🇸", "global": "🌍"
            }
            c_flag = "🌍"
            for k, f in flag_mapping.items():
                if k in str(country).lower():
                    c_flag = f
                    break
                    
            deadline = s.get("deadline","")
            dl_badge = f'<span class="tag tag-l" style="background:rgba(250,204,21,.15);color:#facc15;border:1px solid rgba(250,204,21,.3);">📅 {deadline}</span>' if deadline else ""
            
            st.markdown(f"""
            <div class="adm-s-card">
                <div class="adm-s-title">{s.get('scholarship_name','—')}</div>
                <div class="adm-s-inst">🏫 {s.get('institution','—')}</div>
                <div>
                    <span class="tag tag-c">{c_flag} {country}</span>
                    <span class="tag tag-l">🎓 {s.get('academic_level','—')}</span>
                    <span class="tag {sc}">● {status_val.upper()}</span>
                    {dl_badge}
                </div>
                <div style="margin-top: 0.6rem; font-size: 0.8rem; color:#94a3b8;">
                    <strong>Enlace oficial:</strong> <a href="{s.get('source_url','#')}" target="_blank" style="color:#9DFF00;text-decoration:none;">{s.get('source_url')}</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
