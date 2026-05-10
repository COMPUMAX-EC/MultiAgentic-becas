from __future__ import annotations


CREATE_TABLE_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_hash TEXT NOT NULL UNIQUE,
        nationality TEXT,
        country_of_residence TEXT,
        academic_level TEXT,
        field_of_study TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS search_queries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_hash TEXT NOT NULL,
        query TEXT NOT NULL,
        target_country TEXT,
        priority INTEGER,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL UNIQUE,
        domain TEXT,
        title TEXT,
        snippet TEXT,
        source_type TEXT,
        reliability_score INTEGER,
        relevance_score INTEGER,
        decision TEXT,
        created_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS untrusted_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT,
        domain TEXT,
        rejection_reason TEXT NOT NULL,
        source_type TEXT,
        first_seen_at TEXT NOT NULL,
        last_checked_at TEXT NOT NULL,
        UNIQUE(url),
        UNIQUE(domain)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scholarships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scholarship_hash TEXT NOT NULL UNIQUE,
        scholarship_name TEXT NOT NULL,
        institution TEXT,
        country TEXT,
        academic_level TEXT,
        eligible_nationalities_json TEXT,
        required_languages_json TEXT,
        fields_json TEXT,
        benefits_json TEXT,
        deadline TEXT,
        requirements_json TEXT,
        application_status TEXT,
        source_url TEXT NOT NULL,
        source_type TEXT,
        source_reliability_score INTEGER,
        extraction_confidence INTEGER,
        evidence_snippets_json TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS extraction_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_hash TEXT NOT NULL,
        source_url TEXT NOT NULL,
        status TEXT NOT NULL,
        scholarships_found INTEGER NOT NULL,
        error TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ranking_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_signature TEXT NOT NULL,
        scholarship_key TEXT NOT NULL,
        scholarship_name TEXT,
        compatibility_score INTEGER,
        compatibility_points INTEGER,
        max_possible_points INTEGER,
        matched_profile_fields_json TEXT,
        missing_profile_fields_json TEXT,
        source_trust_score INTEGER,
        deadline_status TEXT,
        display_link TEXT,
        source_url TEXT,
        official_link TEXT,
        application_url TEXT,
        pdf_url TEXT,
        final_score INTEGER,
        priority_label TEXT,
        last_checked_at TEXT NOT NULL,
        UNIQUE(profile_signature, scholarship_key)
    )
    """,
    # ── Auth: Google-authenticated users ─────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        google_sub    TEXT    UNIQUE NOT NULL,
        email         TEXT    NOT NULL,
        name          TEXT,
        picture_url   TEXT,
        created_at    TEXT    NOT NULL,
        last_login_at TEXT    NOT NULL
    )
    """,
    # ── Auth: per-user daily query log ───────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS user_queries (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        google_sub TEXT NOT NULL REFERENCES users(google_sub) ON DELETE CASCADE,
        query_hash TEXT NOT NULL,
        used_at    TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_user_queries_sub
    ON user_queries(google_sub, used_at)
    """,
)
