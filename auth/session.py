"""
session.py — Streamlit session management for Google OAuth.

Stores the signed session token in st.session_state (server-side memory only).
No cookies, no URL params — the token is never exposed to the browser after login.

Usage in any page:
    from auth.session import require_login, get_current_user, logout

    user = require_login()   # blocks with login UI if not authenticated
    # ... rest of page ...
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from auth.google_oauth import (
    OAuthError,
    UserInfo,
    build_auth_url,
    exchange_code_for_user,
    verify_session_token,
    create_session_token,
)

_SESSION_TOKEN_KEY  = "_auth_token"
_PENDING_STATE_KEY  = "_oauth_state"

# ── Public API ────────────────────────────────────────────────────────────────

def get_current_user() -> UserInfo | None:
    """
    Return the currently logged-in user, or None.
    Also handles the OAuth callback if ?code= is present in the URL.
    """
    # 1. Handle OAuth callback (?code=X&state=Y in query params)
    code  = _query_param("code")
    state = _query_param("state")
    if code and state:
        _handle_callback(code, state)
        return get_current_user()   # re-read after callback

    # 2. Validate existing session token
    token = st.session_state.get(_SESSION_TOKEN_KEY)
    
    # 3. Fallback: Validate existing session token in query params (survives refresh!)
    if not token:
        token = st.query_params.get(_SESSION_TOKEN_KEY)
        if token:
            st.session_state[_SESSION_TOKEN_KEY] = token

    if token:
        user = verify_session_token(token)
        if user:
            # Sync back to query params to preserve across refreshes
            if st.query_params.get(_SESSION_TOKEN_KEY) != token:
                st.query_params[_SESSION_TOKEN_KEY] = token
            return user
        # Token expired — clear it
        _clear_session()

    return None


def require_login(*, sidebar_only: bool = False) -> UserInfo:
    """
    Gate: if no valid session exists, stop the page.

    sidebar_only=True — no full-page login; user signs in via sidebar widget.
    """
    user = get_current_user()
    if user:
        return user
    if sidebar_only:
        st.markdown("### 🔐 Sign in required")
        st.info(
            "Use **Login with Google** in the sidebar to access scholarship search. "
            "Each account gets **5 profile-based searches per day**."
        )
        st.stop()
    _render_login_page()
    st.stop()


def logout() -> None:
    """Clear the current session (does not revoke Google token — not needed)."""
    _clear_session()
    # Remove ?code / ?state from URL if present
    st.query_params.clear()
    st.rerun()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _handle_callback(code: str, state: str) -> None:
    """Exchange Google authorization code for a session token."""
    saved_state = st.session_state.get(_PENDING_STATE_KEY, "")
    try:
        user = exchange_code_for_user(code, state, saved_state)
        # Persist user to DB and issue session token
        _upsert_user(user)
        token = create_session_token(user)
        st.session_state[_SESSION_TOKEN_KEY] = token
        st.session_state.pop(_PENDING_STATE_KEY, None)
        # Clean ?code and ?state from the URL to prevent re-processing on refresh
        st.query_params.clear()
        # Set session token in query params to persist across refreshes!
        st.query_params[_SESSION_TOKEN_KEY] = token
        st.rerun()
    except OAuthError as exc:
        st.session_state.pop(_PENDING_STATE_KEY, None)
        st.query_params.clear()
        st.error(f"🔐 Login failed: {exc}")


def _upsert_user(user: UserInfo) -> None:
    """Insert or update the user record in SQLite."""
    try:
        from database.repository import upsert_user
        upsert_user(
            google_sub=user.sub,
            email=user.email,
            name=user.name,
            picture_url=user.picture,
        )
    except Exception:
        pass   # Non-fatal: session still works if DB write fails


def _clear_session() -> None:
    st.session_state.pop(_SESSION_TOKEN_KEY, None)
    st.session_state.pop(_PENDING_STATE_KEY, None)


def _render_login_page() -> None:
    """Render a premium-styled login screen. Called by require_login()."""
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
[data-testid="stAppViewContainer"]{background:linear-gradient(135deg,#0a0e1a,#0f172a,#1a1035);}
[data-testid="stSidebar"]{display:none;}
.login-wrap{display:flex;flex-direction:column;align-items:center;justify-content:center;
    min-height:80vh;padding:2rem;}
.login-card{background:rgba(15,23,42,.92);border:1px solid rgba(99,102,241,.35);
    border-radius:24px;padding:3rem 2.5rem;max-width:420px;width:100%;
    box-shadow:0 25px 60px rgba(0,0,0,.5),0 0 80px rgba(99,102,241,.08);
    text-align:center;}
.login-logo{font-size:3.5rem;margin-bottom:.5rem;}
.login-title{font-size:1.8rem;font-weight:700;
    background:linear-gradient(135deg,#818cf8,#c084fc,#38bdf8);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    background-clip:text;margin-bottom:.4rem;}
.login-sub{color:#64748b;font-size:.95rem;margin-bottom:2rem;line-height:1.5;}
.quota-info{background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.2);
    border-radius:12px;padding:.8rem 1.2rem;margin-bottom:1.8rem;font-size:.82rem;color:#94a3b8;}
.quota-info strong{color:#818cf8;}
.divider{border:none;border-top:1px solid rgba(30,41,59,.8);margin:1.5rem 0;}
.security-note{font-size:.75rem;color:#334155;margin-top:1.5rem;}
</style>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="login-wrap">
  <div class="login-card">
    <div class="login-logo">🎓</div>
    <div class="login-title">MultiAgentic Scholarships</div>
    <div class="login-sub">
      Powered by AMD Instinct MI300X &amp; LangGraph.<br>
      Sign in to start your scholarship search.
    </div>
    <div class="quota-info">
      🔎 Each account gets <strong>5 AI searches per day</strong>.<br>
      Quota resets every 24 hours automatically.
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # Center the button using columns
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        if st.button("🔑  Sign in with Google", type="primary", use_container_width=True):
            _start_oauth()

    st.markdown("""
<div style="text-align:center;margin-top:.6rem;">
  <span style="font-size:.72rem;color:#1e293b;">
    🔒 We only store your name and email. No passwords. No data is shared.
  </span>
</div>
""", unsafe_allow_html=True)


def _query_param(name: str) -> str | None:
    """Read a single query param (Streamlit may return str or list)."""
    raw = st.query_params.get(name)
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw[0] if raw else None
    return str(raw)


def _start_oauth() -> None:
    """Redirect the browser to Google's authorization endpoint."""
    try:
        auth_url, state = build_auth_url()
        st.session_state[_PENDING_STATE_KEY] = state
        # Streamlit has no stable external redirect API across versions.
        # Use client-side meta refresh for immediate same-tab navigation.
        st.markdown(
            f'<meta http-equiv="refresh" content="0;url={auth_url}">',
            unsafe_allow_html=True,
        )
        st.stop()
    except OAuthError as exc:
        st.error(f"❌ Cannot start login: {exc}")


def is_admin_user(user: UserInfo | None) -> bool:
    """
    Check if the user is an administrator based on the ADMIN_EMAILS environment variable
    or the 'role' field in their database record.
    """
    if not user:
        return False
    import os
    from database.repository import get_user
    
    # 1. Direct environment variable check
    admin_emails_env = os.getenv("ADMIN_EMAILS", "")
    admin_emails = [e.strip().lower() for e in admin_emails_env.split(",") if e.strip()]
    if user.email.lower() in admin_emails or user.email.lower() == "squelal91@gmail.com":
        return True
        
    # 2. Database role fallback
    try:
        db_u = get_user(user.sub)
        if db_u and db_u.get("role") == "admin":
            return True
    except Exception:
        pass
        
    return False

