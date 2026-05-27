from __future__ import annotations

import importlib
import sys

import pytest


def load_google_oauth(monkeypatch, *, session_secret: str | None) -> object:
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:8501/")

    if session_secret is None:
        monkeypatch.delenv("SESSION_SECRET_KEY", raising=False)
    else:
        monkeypatch.setenv("SESSION_SECRET_KEY", session_secret)

    sys.modules.pop("auth.google_oauth", None)
    return importlib.import_module("auth.google_oauth")


def test_build_auth_url_accepts_gcp_env_aliases(monkeypatch) -> None:
    monkeypatch.setenv("GCP_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GCP_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("SESSION_SECRET_KEY", "c" * 64)
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:8501/")

    sys.modules.pop("auth.google_oauth", None)
    google_oauth = importlib.import_module("auth.google_oauth")

    auth_url, state = google_oauth.build_auth_url()

    assert "client_id=test-client-id.apps.googleusercontent.com" in auth_url
    assert state


def test_build_auth_url_requires_session_secret(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    google_oauth = load_google_oauth(monkeypatch, session_secret=None)

    with pytest.raises(google_oauth.OAuthError, match="SESSION_SECRET_KEY"):
        google_oauth.build_auth_url()


def test_session_token_round_trip(monkeypatch) -> None:
    google_oauth = load_google_oauth(monkeypatch, session_secret="a" * 64)

    user = google_oauth.UserInfo(
        sub="google-sub-123",
        email="student@example.com",
        name="Student Example",
        picture="https://example.com/avatar.png",
        email_verified=True,
    )

    token = google_oauth.create_session_token(user)

    assert google_oauth.verify_session_token(token) == user


def test_session_token_rejects_tampering(monkeypatch) -> None:
    google_oauth = load_google_oauth(monkeypatch, session_secret="b" * 64)

    user = google_oauth.UserInfo(
        sub="google-sub-123",
        email="student@example.com",
        name="Student Example",
        picture="",
        email_verified=True,
    )

    token = google_oauth.create_session_token(user)
    payload, signature = token.rsplit(".", 1)
    tampered_payload = payload[:-1] + ("A" if payload[-1] != "A" else "B")

    assert google_oauth.verify_session_token(f"{tampered_payload}.{signature}") is None