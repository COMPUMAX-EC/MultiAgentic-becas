"""
google_oauth.py — Google OAuth 2.0 Authorization Code flow for Streamlit.

Security design:
  • state  parameter: HMAC-SHA256(nonce + timestamp, SESSION_SECRET_KEY) → prevents CSRF
  • code exchange: server-side only (never exposed in frontend)
  • userinfo: validates email_verified=True (rejects unverified Google accounts)
  • session token: HMAC-SHA256(payload + expiry, SESSION_SECRET_KEY) — stateless, 8 h TTL
  • google_sub used as user identifier (immutable, unlike email)
  • no Google tokens stored anywhere — only sub + email in SQLite
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass

# ── Constants ─────────────────────────────────────────────────────────────────
_GOOGLE_AUTH_URL   = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL  = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", os.getenv("GCP_CLIENT_ID", ""))
_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", os.getenv("GCP_CLIENT_SECRET", ""))
_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501/")
_SECRET_KEY    = os.getenv("SESSION_SECRET_KEY", "").strip()
_TOKEN_TTL_S   = 8 * 3600   # 8-hour session


class OAuthError(RuntimeError):
    """Raised on any OAuth flow or token validation failure."""


@dataclass(frozen=True)
class UserInfo:
    sub: str          # Google's stable user ID
    email: str
    name: str
    picture: str
    email_verified: bool


def _require_secret_key() -> str:
    """Return the signing secret or fail fast with a configuration error."""
    if not _SECRET_KEY:
        raise OAuthError(
            "SESSION_SECRET_KEY is not set. Add it to your .env file and restart the app."
        )
    return _SECRET_KEY


# ── State (CSRF) helpers ──────────────────────────────────────────────────────

def _sign(message: str) -> str:
    """Return HMAC-SHA256 hex digest of message using SESSION_SECRET_KEY."""
    secret_key = _require_secret_key()
    return hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()


def build_state_token() -> str:
    """
    Generate a signed CSRF state token.
    Format: <timestamp>.<nonce>.<signature>
    """
    import secrets
    nonce = secrets.token_hex(16)
    ts    = str(int(time.time()))
    payload = f"{ts}.{nonce}"
    sig = _sign(payload)
    return f"{payload}.{sig}"


def verify_state_token(state: str, max_age_s: int = 600) -> bool:
    """
    Verify the CSRF state token returned by Google.
    Returns True only if signature matches and token is not older than max_age_s.
    """
    try:
        parts = state.split(".")
        if len(parts) != 3:
            return False
        ts_str, nonce, received_sig = parts
        expected_sig = _sign(f"{ts_str}.{nonce}")
        # Constant-time comparison
        if not hmac.compare_digest(expected_sig, received_sig):
            return False
        age = int(time.time()) - int(ts_str)
        return 0 <= age <= max_age_s
    except Exception:
        return False


# ── Authorization URL ─────────────────────────────────────────────────────────

def build_auth_url() -> tuple[str, str]:
    """
    Build the Google OAuth 2.0 authorization URL.

    Returns:
        (auth_url, state_token) — persist state_token to verify callback
    """
    if not _CLIENT_ID:
        raise OAuthError(
            "GOOGLE_CLIENT_ID / GCP_CLIENT_ID is not set. "
            "Add it to your .env file (see .env.example)."
        )
    state = build_state_token()
    params = {
        "client_id":     _CLIENT_ID,
        "redirect_uri":  _REDIRECT_URI,
        "response_type": "code",
        "scope":         "openid email profile",
        "state":         state,
        "access_type":   "online",
        "prompt":        "select_account",   # Always show account picker
    }
    url = f"{_GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return url, state


# ── Code exchange ─────────────────────────────────────────────────────────────

def _post_json(url: str, data: dict) -> dict:
    """POST JSON-encoded data to url, return parsed response dict."""
    body = urllib.parse.urlencode(data).encode()
    req  = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body_text = ""
        try:
            body_text = exc.read().decode(errors="ignore")
        except Exception:
            pass
        raise OAuthError(f"HTTP {exc.code} from {url}: {body_text}") from exc
    except Exception as exc:
        raise OAuthError(f"Network error contacting {url}: {exc}") from exc


def _get_json(url: str, access_token: str) -> dict:
    """GET url with Bearer token, return parsed response dict."""
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        raise OAuthError(f"Failed to fetch userinfo: {exc}") from exc


def exchange_code_for_user(code: str, state: str, saved_state: str) -> UserInfo:
    """
    Complete the OAuth callback:
      1. Verify CSRF state
      2. Exchange authorization code for access token
      3. Fetch and validate userinfo

    Args:
        code:        Authorization code from query params
        state:       State value from query params (returned by Google)
        saved_state: State value stored in st.session_state before redirect

    Returns:
        UserInfo with verified Google account details

    Raises:
        OAuthError on any validation or network failure
    """
    # 1. CSRF check — state from Google must match what we generated
    if not saved_state or state != saved_state:
        raise OAuthError("CSRF state mismatch — possible cross-site request forgery.")
    if not verify_state_token(state):
        raise OAuthError("OAuth state token is invalid or expired.")

    # 2. Exchange code → access_token
    if not _CLIENT_SECRET:
        raise OAuthError(
            "GOOGLE_CLIENT_SECRET / GCP_CLIENT_SECRET is not set. Add it to your .env file."
        )
    token_resp = _post_json(_GOOGLE_TOKEN_URL, {
        "code":          code,
        "client_id":     _CLIENT_ID,
        "client_secret": _CLIENT_SECRET,
        "redirect_uri":  _REDIRECT_URI,
        "grant_type":    "authorization_code",
    })
    access_token = token_resp.get("access_token")
    if not access_token:
        raise OAuthError(f"Token exchange failed: {token_resp.get('error', 'unknown')}")

    # 3. Fetch userinfo — validate email_verified
    info = _get_json(_GOOGLE_USERINFO_URL, access_token)
    if not info.get("email_verified", False):
        raise OAuthError(
            "Google account email is not verified. "
            "Only verified Google accounts are allowed."
        )
    sub = info.get("sub")
    if not sub:
        raise OAuthError("Google userinfo did not return a user ID (sub).")

    return UserInfo(
        sub=sub,
        email=info.get("email", ""),
        name=info.get("name", info.get("email", "")),
        picture=info.get("picture", ""),
        email_verified=True,
    )


# ── Session token (stateless, HMAC-signed) ────────────────────────────────────

def create_session_token(user: UserInfo) -> str:
    """
    Create a signed session token valid for _TOKEN_TTL_S seconds.
    Format (URL-safe): base64(json_payload).HMAC-SHA256
    We keep it simple — no external JWT lib needed.
    """
    import base64
    expires_at = int(time.time()) + _TOKEN_TTL_S
    payload = json.dumps({
        "sub":     user.sub,
        "email":   user.email,
        "name":    user.name,
        "picture": user.picture,
        "exp":     expires_at,
    }, separators=(",", ":"))
    b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    sig = _sign(b64)
    return f"{b64}.{sig}"


def verify_session_token(token: str) -> UserInfo | None:
    """
    Verify a session token.  Returns UserInfo if valid, None otherwise.
    Never raises — safe to call on untrusted input.
    """
    import base64
    try:
        b64, received_sig = token.rsplit(".", 1)
        expected_sig = _sign(b64)
        if not hmac.compare_digest(expected_sig, received_sig):
            return None
        # Restore padding
        padding = 4 - len(b64) % 4
        payload = json.loads(base64.urlsafe_b64decode(b64 + "=" * padding).decode())
        if int(time.time()) > payload.get("exp", 0):
            return None   # expired
        return UserInfo(
            sub=payload["sub"],
            email=payload["email"],
            name=payload["name"],
            picture=payload.get("picture", ""),
            email_verified=True,
        )
    except Exception:
        return None
