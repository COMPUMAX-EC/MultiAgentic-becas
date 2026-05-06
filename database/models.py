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
)
