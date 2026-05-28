"""
auth_ui.py — Reusable sidebar authentication widget.

Call render_auth_sidebar() inside a `with st.sidebar:` block on any page.
It shows:
  • If NOT logged in: a compact "Login with Google" button
  • If logged in:     avatar, name, email, daily quota progress bar, Logout button
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st


def render_auth_sidebar() -> None:
    """
    Render the auth panel inside the sidebar.
    Must be called inside a `with st.sidebar:` block.
    """
    from auth.session import get_current_user, logout, _start_oauth
    from auth.quota import get_quota_status

    user = get_current_user()

    st.markdown("---")

    if user is None:
        st.markdown(
            "<div style='font-size:.8rem;color:#64748b;margin-bottom:.5rem;'>"
            "🔐 Sign in to search (5/day)</div>",
            unsafe_allow_html=True,
        )
        if st.button("🔑 Login with Google", use_container_width=True, key="sb_login_btn"):
            _start_oauth()
        return

    status = get_quota_status(user.sub)
    used = status["used"]
    limit = status["limit"]
    remaining = status["remaining"]

    avatar_html = (
        f'<img src="{user.picture}" width="36" height="36" '
        f'style="border-radius:50%;border:2px solid rgba(99,102,241,.5);'
        f'vertical-align:middle;margin-right:.5rem;">'
        if user.picture else "👤 "
    )
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:.4rem;"
        f"background:rgba(15,23,42,.7);border-radius:10px;padding:.5rem .7rem;"
        f"border:1px solid rgba(99,102,241,.2);margin-bottom:.5rem;'>"
        f"{avatar_html}"
        f"<div>"
        f"<div style='font-size:.82rem;font-weight:600;color:#e2e8f0;'>{user.name}</div>"
        f"<div style='font-size:.7rem;color:#64748b;'>{user.email}</div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    quota_color = (
        "#4ade80" if remaining > 2 else
        "#facc15" if remaining > 0 else
        "#ef4444"
    )
    pct = int((used / limit) * 100) if limit else 0
    st.markdown(
        f"<div style='margin-bottom:.6rem;'>"
        f"<div style='display:flex;justify-content:space-between;"
        f"font-size:.72rem;color:#64748b;margin-bottom:.3rem;'>"
        f"<span>🔎 Búsquedas hoy</span>"
        f"<span style='color:{quota_color};font-weight:600;'>{used}/{limit}</span>"
        f"</div>"
        f"<div style='background:rgba(30,41,59,.8);border-radius:6px;height:6px;overflow:hidden;'>"
        f"<div style='width:{pct}%;height:100%;background:{quota_color};"
        f"border-radius:6px;transition:width .4s;'></div>"
        f"</div>"
        f"<div style='font-size:.68rem;color:#334155;margin-top:.25rem;'>"
        f"{'✅ ' + str(remaining) + ' restantes' if remaining > 0 else '⛔ Cuota agotada — reinicia en <24h'}"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    if st.button("↩ Cerrar sesión", use_container_width=True, key="sb_logout_btn"):
        logout()
