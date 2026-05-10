"""
quota.py — Per-user daily query quota enforcement.

Limit: MAX_QUERIES_PER_USER searches per rolling 24-hour window.
Identified by google_sub (immutable Google ID, not email).

Usage:
    from auth.quota import QuotaExceededError, get_quota_status, consume_query

    status = get_quota_status(user.sub)   # {"used": 3, "limit": 5, "remaining": 2}
    consume_query(user.sub, query_text)    # raises QuotaExceededError if limit hit
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

MAX_QUERIES: int = int(os.getenv("MAX_QUERIES_PER_USER", "5"))
_WINDOW_HOURS: int = 24


class QuotaExceededError(RuntimeError):
    """Raised when a user has exhausted their daily query allowance."""
    def __init__(self, used: int, limit: int) -> None:
        self.used  = used
        self.limit = limit
        super().__init__(
            f"Daily quota exceeded: {used}/{limit} searches used. "
            f"Resets in less than 24 hours."
        )


def _hash_query(query_text: str) -> str:
    """SHA-256 hash of the query text — we never store queries in plaintext."""
    return hashlib.sha256(query_text.strip().lower().encode()).hexdigest()


def get_quota_status(google_sub: str) -> dict:
    """
    Return a dict with quota stats for the user in the last 24 hours:
        {"used": int, "limit": int, "remaining": int, "window_hours": int}
    """
    from database.repository import get_daily_query_count
    used = get_daily_query_count(google_sub, window_hours=_WINDOW_HOURS)
    remaining = max(0, MAX_QUERIES - used)
    return {
        "used":         used,
        "limit":        MAX_QUERIES,
        "remaining":    remaining,
        "window_hours": _WINDOW_HOURS,
    }


def check_quota(google_sub: str) -> bool:
    """Return True if the user still has queries available today."""
    status = get_quota_status(google_sub)
    return status["remaining"] > 0


def consume_query(google_sub: str, query_text: str) -> None:
    """
    Record a query consumption for the user.

    Raises:
        QuotaExceededError: if the daily limit has already been reached.
    """
    status = get_quota_status(google_sub)
    if status["remaining"] <= 0:
        raise QuotaExceededError(status["used"], status["limit"])

    from database.repository import record_user_query
    record_user_query(google_sub, _hash_query(query_text))
