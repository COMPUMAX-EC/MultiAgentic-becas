"""header_ui.py — Reusable premium top navigation header component showing DevIALabs branding and user applied scholarships."""
from __future__ import annotations

import streamlit as st


@st.cache_data
def _get_bg_base64() -> str:
    from pathlib import Path
    import base64
    try:
        bg_path = Path(__file__).resolve().parents[2] / "fondo.png"
        if bg_path.exists():
            with open(bg_path, "rb") as f:
                return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    except Exception:
        pass
    return ""


def render_custom_header() -> None:
    """
    Render a premium status/navigation header block at the top of the page.
    Displays DevIALabs brand identity, logged-in user profile, and applied scholarships dropdown.
    """
    from auth.session import get_current_user
    from database.repository import get_user_profile

    user = get_current_user()
    applied = st.session_state.get("applied_scholarships", [])

    bg_uri = _get_bg_base64()
    if bg_uri:
        st.markdown(f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background: linear-gradient(135deg, rgba(5, 5, 5, 0.92), rgba(26, 26, 26, 0.92)), url("{bg_uri}") no-repeat center center fixed !important;
            background-size: cover !important;
        }}
        </style>
        """, unsafe_allow_html=True)

    # Custom CSS for the premium top header
    st.markdown("""
    <style>
    .top-header {
        background: #1A1A1A;
        border: 1px solid rgba(157, 255, 0, 0.25);
        border-radius: 16px;
        padding: 0.8rem 1.5rem;
        margin-bottom: 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }
    .header-left {
        display: flex;
        align-items: center;
        gap: 0.8rem;
    }
    .brand-logo {
        font-size: 1.4rem;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .brand-logo .dev { color: #9DFF00; }
    .brand-logo .ia { color: #FFFFFF; }
    .brand-logo .labs { color: #9DFF00; }
    .header-right {
        display: flex;
        align-items: center;
        gap: 1.2rem;
    }
    .dropdown-container {
        position: relative;
    }
    details.header-dropdown {
        user-select: none;
    }
    details.header-dropdown summary {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        cursor: pointer;
        list-style: none;
        background: rgba(157, 255, 0, 0.08);
        border: 1px solid rgba(157, 255, 0, 0.25);
        border-radius: 12px;
        padding: 0.4rem 1rem;
        color: #FFFFFF;
        font-size: 0.88rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    details.header-dropdown summary:hover {
        background: rgba(157, 255, 0, 0.18);
        border-color: #9DFF00;
        box-shadow: 0 0 10px rgba(157, 255, 0, 0.2);
    }
    details.header-dropdown summary::-webkit-details-marker {
        display: none;
    }
    .dd-badge {
        background: #9DFF00;
        color: #050505;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 0.1rem 0.45rem;
        border-radius: 50px;
    }
    .dd-content {
        position: absolute;
        right: 0;
        top: 115%;
        background: #1A1A1A;
        border: 1px solid rgba(157, 255, 0, 0.3);
        border-radius: 12px;
        padding: 1rem;
        width: 320px;
        z-index: 99999;
        box-shadow: 0 8px 32px rgba(0,0,0,0.6);
    }
    .dd-profile-info {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        padding-bottom: 0.8rem;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 0.8rem;
    }
    .dd-avatar {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        border: 2px solid #9DFF00;
        object-fit: cover;
    }
    .dd-default-avatar {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        border: 2px solid #9DFF00;
        background: rgba(157, 255, 0, 0.1);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
    }
    .dd-name {
        font-size: 0.85rem;
        font-weight: 600;
        color: #FFFFFF;
        text-align: left;
    }
    .dd-email {
        font-size: 0.72rem;
        color: #94A3B8;
        text-align: left;
    }
    .dd-level {
        font-size: 0.7rem;
        background: rgba(157, 255, 0, 0.15);
        color: #9DFF00;
        padding: 0.1rem 0.4rem;
        border-radius: 4px;
        display: inline-block;
        margin-top: 0.2rem;
        text-align: left;
    }
    .dd-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: #9DFF00;
        margin-bottom: 0.5rem;
        text-align: left;
    }
    .dd-list {
        max-height: 180px;
        overflow-y: auto;
        list-style: none;
        padding: 0;
        margin: 0;
        text-align: left;
    }
    .dd-item {
        padding: 0.5rem;
        border-radius: 6px;
        background: rgba(255,255,255,0.03);
        margin-bottom: 0.4rem;
        border: 1px solid rgba(255,255,255,0.05);
        transition: all 0.2s ease;
    }
    .dd-item:hover {
        background: rgba(157, 255, 0, 0.05);
        border-color: rgba(157, 255, 0, 0.2);
    }
    .dd-item-name {
        font-size: 0.78rem;
        font-weight: 600;
        color: #E2E8F0;
        line-height: 1.2;
    }
    .dd-item-meta {
        display: flex;
        justify-content: space-between;
        font-size: 0.65rem;
        color: #64748B;
        margin-top: 0.2rem;
    }
    .dd-empty {
        font-size: 0.75rem;
        color: #64748B;
        text-align: center;
        padding: 1rem 0;
        font-style: italic;
    }
    </style>
    """, unsafe_allow_html=True)

    # Render user profile avatar and metadata inside the dd-profile-info section
    if user:
        profile_level = "No especificado"
        try:
            db_profile = get_user_profile(user.sub)
            if db_profile and db_profile.get("academic_level"):
                raw_lvl = db_profile.get("academic_level").lower().strip()
                mapping = {
                    "high school": "Bachillerato",
                    "bachelors": "Pregrado",
                    "masters": "Maestría",
                    "phd": "Doctorado"
                }
                profile_level = mapping.get(raw_lvl, db_profile.get("academic_level").title())
        except Exception:
            pass

        avatar_img = f'<img src="{user.picture}" class="dd-avatar">' if user.picture else '<div class="dd-default-avatar">👤</div>'
        profile_section = (
            f'<div class="dd-profile-info">'
            f'{avatar_img}'
            f'<div>'
            f'<div class="dd-name">{user.name}</div>'
            f'<div class="dd-email">{user.email}</div>'
            f'<div class="dd-level">🎓 {profile_level}</div>'
            f'</div>'
            f'</div>'
        )
        trigger_label = f"👤 {user.name.split()[0]} &nbsp;<span class='dd-badge'>{len(applied)}</span>"
    else:
        profile_section = (
            '<div class="dd-profile-info">'
            '<div class="dd-default-avatar">👤</div>'
            '<div>'
            '<div class="dd-name">Invitado</div>'
            '<div class="dd-email">Inicia sesión en la barra lateral</div>'
            '</div>'
            '</div>'
        )
        trigger_label = "👤 Cuenta"

    # Render applied scholarships list
    applied_list_items = ""
    if applied:
        for item in applied:
            applied_list_items += (
                f'<li class="dd-item">'
                f'<div class="dd-item-name">{item["scholarship_name"]}</div>'
                f'<div class="dd-item-meta">'
                f'<span>🌍 {item.get("country", "Global")}</span>'
                f'<span>📅 {item.get("date", "")}</span>'
                f'</div>'
                f'</li>'
            )
    else:
        applied_list_items = '<div class="dd-empty">No has preparado postulaciones aún.</div>'

    # Full Header HTML Structure without newlines to prevent markdown code block formatting
    header_html = (
        f'<div class="top-header">'
        f'<div class="header-left">'
        f'<span class="brand-logo"><span class="dev">Dev</span><span class="ia">IA</span><span class="labs">labs</span></span>'
        f'</div>'
        f'<div class="header-right">'
        f'<div class="dropdown-container">'
        f'<details class="header-dropdown">'
        f'<summary>{trigger_label}</summary>'
        f'<div class="dd-content">'
        f'{profile_section}'
        f'<div class="dd-title">📝 Becas Postuladas ({len(applied)})</div>'
        f'<ul class="dd-list">{applied_list_items}</ul>'
        f'</div>'
        f'</details>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)
