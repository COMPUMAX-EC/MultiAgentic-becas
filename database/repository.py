from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from database.connection import close_connection, get_connection
from database.migrations import run_migrations
from utils.hash_utils import profile_hash as build_profile_hash
from utils.hash_utils import scholarship_hash as build_scholarship_hash
from utils.url_utils import extract_domain


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_database(db_path: str | Path | None = None) -> None:
    run_migrations(db_path)


def save_profile(profile: dict, db_path: str | Path | None = None) -> str:
    profile_hash = build_profile_hash(profile)
    connection = get_connection(db_path)
    try:
        connection.execute(
            """
            INSERT OR IGNORE INTO profiles (
                profile_hash, nationality, country_of_residence,
                academic_level, field_of_study, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                profile_hash,
                profile.get("nationality"),
                profile.get("country_of_residence"),
                profile.get("academic_level"),
                profile.get("field_of_study"),
                _now_iso(),
            ),
        )
        connection.commit()
        return profile_hash
    finally:
        close_connection(connection)


def save_search_queries(
    profile_hash: str, queries: list[dict], db_path: str | Path | None = None
) -> int:
    connection = get_connection(db_path)
    try:
        created_at = _now_iso()
        connection.executemany(
            """
            INSERT INTO search_queries (profile_hash, query, target_country, priority, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    profile_hash,
                    query.get("query"),
                    query.get("target_country"),
                    query.get("priority"),
                    created_at,
                )
                for query in queries
            ],
        )
        connection.commit()
        return len(queries)
    finally:
        close_connection(connection)


def save_sources(sources: list[dict], db_path: str | Path | None = None) -> int:
    connection = get_connection(db_path)
    try:
        saved_count = 0
        now = _now_iso()
        for source in sources:
            url = source.get("url")
            if not url:
                continue
            existing = connection.execute(
                "SELECT id FROM sources WHERE url = ?", (url,)
            ).fetchone()
            domain = extract_domain(url)
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO sources (
                        url, domain, title, snippet, source_type,
                        reliability_score, relevance_score, decision,
                        created_at, last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        url,
                        domain,
                        source.get("title"),
                        source.get("snippet"),
                        source.get("source_type"),
                        source.get("reliability_score"),
                        source.get("relevance_score"),
                        source.get("decision"),
                        now,
                        now,
                    ),
                )
            else:
                connection.execute(
                    """
                    UPDATE sources
                    SET domain = ?, title = ?, snippet = ?, source_type = ?,
                        reliability_score = ?, relevance_score = ?, decision = ?,
                        last_seen_at = ?
                    WHERE url = ?
                    """,
                    (
                        domain,
                        source.get("title"),
                        source.get("snippet"),
                        source.get("source_type"),
                        source.get("reliability_score"),
                        source.get("relevance_score"),
                        source.get("decision"),
                        now,
                        url,
                    ),
                )
            saved_count += 1

        connection.commit()
        return saved_count
    finally:
        close_connection(connection)


def save_untrusted_source(
    url: str | None,
    domain: str | None,
    rejection_reason: str,
    source_type: str,
    db_path: str | Path | None = None,
) -> None:
    init_database(db_path)
    connection = get_connection(db_path)
    try:
        now = _now_iso()
        cleaned_url = str(url or "").strip() or None
        cleaned_domain = str(domain or "").strip().lower() or None
        if cleaned_url is None and cleaned_domain is None:
            return

        existing = connection.execute(
            """
            SELECT id FROM untrusted_sources
            WHERE (? IS NOT NULL AND url = ?)
               OR (? IS NOT NULL AND domain = ?)
            LIMIT 1
            """,
            (cleaned_url, cleaned_url, cleaned_domain, cleaned_domain),
        ).fetchone()

        if existing is None:
            connection.execute(
                """
                INSERT INTO untrusted_sources (
                    url, domain, rejection_reason, source_type,
                    first_seen_at, last_checked_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    cleaned_url,
                    cleaned_domain,
                    rejection_reason,
                    source_type,
                    now,
                    now,
                ),
            )
        else:
            connection.execute(
                """
                UPDATE untrusted_sources
                SET rejection_reason = ?, source_type = ?, last_checked_at = ?
                WHERE id = ?
                """,
                (rejection_reason, source_type, now, existing["id"]),
            )
        connection.commit()
    finally:
        close_connection(connection)


def get_untrusted_source_match(
    url: str | None,
    domain: str | None,
    db_path: str | Path | None = None,
) -> dict | None:
    init_database(db_path)
    connection = get_connection(db_path)
    try:
        cleaned_url = str(url or "").strip() or None
        cleaned_domain = str(domain or "").strip().lower() or None
        if cleaned_url is None and cleaned_domain is None:
            return None

        row = connection.execute(
            """
            SELECT * FROM untrusted_sources
            WHERE (? IS NOT NULL AND url = ?)
               OR (? IS NOT NULL AND domain = ?)
            LIMIT 1
            """,
            (cleaned_url, cleaned_url, cleaned_domain, cleaned_domain),
        ).fetchone()
        if row is None:
            return None

        now = _now_iso()
        connection.execute(
            "UPDATE untrusted_sources SET last_checked_at = ? WHERE id = ?",
            (now, row["id"]),
        )
        connection.commit()
        return dict(row)
    finally:
        close_connection(connection)


def save_scholarships(
    scholarships: list[dict], db_path: str | Path | None = None
) -> dict:
    connection = get_connection(db_path)
    try:
        inserted = 0
        updated = 0
        now = _now_iso()

        for scholarship in scholarships:
            scholarship_id = build_scholarship_hash(
                scholarship.get("scholarship_name", ""),
                scholarship.get("source_url", ""),
            )
            existing = get_existing_scholarship_by_hash(
                scholarship_id, db_path=db_path, connection=connection
            )

            insert_payload = (
                scholarship.get("scholarship_name"),
                scholarship.get("institution"),
                scholarship.get("country"),
                scholarship.get("academic_level"),
                json.dumps(scholarship.get("eligible_nationalities", []), ensure_ascii=False),
                json.dumps(scholarship.get("required_languages", []), ensure_ascii=False),
                json.dumps(scholarship.get("fields", []), ensure_ascii=False),
                json.dumps(scholarship.get("benefits", []), ensure_ascii=False),
                scholarship.get("deadline"),
                json.dumps(scholarship.get("requirements", []), ensure_ascii=False),
                scholarship.get("application_status"),
                scholarship.get("source_url"),
                scholarship.get("source_type"),
                scholarship.get("source_reliability_score"),
                scholarship.get("extraction_confidence"),
                json.dumps(scholarship.get("evidence_snippets", []), ensure_ascii=False),
                now,
                now,
                now,
            )

            update_payload = (
                scholarship.get("scholarship_name"),
                scholarship.get("institution"),
                scholarship.get("country"),
                scholarship.get("academic_level"),
                json.dumps(scholarship.get("eligible_nationalities", []), ensure_ascii=False),
                json.dumps(scholarship.get("required_languages", []), ensure_ascii=False),
                json.dumps(scholarship.get("fields", []), ensure_ascii=False),
                json.dumps(scholarship.get("benefits", []), ensure_ascii=False),
                scholarship.get("deadline"),
                json.dumps(scholarship.get("requirements", []), ensure_ascii=False),
                scholarship.get("application_status"),
                scholarship.get("source_url"),
                scholarship.get("source_type"),
                scholarship.get("source_reliability_score"),
                scholarship.get("extraction_confidence"),
                json.dumps(scholarship.get("evidence_snippets", []), ensure_ascii=False),
                now,
                now,
                scholarship_id,
            )

            if existing is None:
                connection.execute(
                    """
                    INSERT INTO scholarships (
                        scholarship_hash, scholarship_name, institution, country,
                        academic_level, eligible_nationalities_json, required_languages_json,
                        fields_json, benefits_json, deadline, requirements_json,
                        application_status, source_url, source_type,
                        source_reliability_score, extraction_confidence,
                        evidence_snippets_json, created_at, updated_at, last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (scholarship_id, *insert_payload),
                )
                inserted += 1
            else:
                connection.execute(
                    """
                    UPDATE scholarships
                    SET scholarship_name = ?, institution = ?, country = ?, academic_level = ?,
                        eligible_nationalities_json = ?, required_languages_json = ?,
                        fields_json = ?, benefits_json = ?, deadline = ?,
                        requirements_json = ?, application_status = ?, source_url = ?,
                        source_type = ?, source_reliability_score = ?,
                        extraction_confidence = ?, evidence_snippets_json = ?,
                        updated_at = ?, last_seen_at = ?
                    WHERE scholarship_hash = ?
                    """,
                    update_payload,
                )
                updated += 1

        connection.commit()
        return {"inserted": inserted, "updated": updated}
    finally:
        close_connection(connection)


def save_extraction_run(
    profile_hash: str,
    source_url: str,
    status: str,
    scholarships_found: int,
    error: str | None = None,
    db_path: str | Path | None = None,
) -> None:
    connection = get_connection(db_path)
    try:
        connection.execute(
            """
            INSERT INTO extraction_runs (
                profile_hash, source_url, status, scholarships_found, error, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (profile_hash, source_url, status, scholarships_found, error, _now_iso()),
        )
        connection.commit()
    finally:
        close_connection(connection)


def save_ranking_records(
    profile_signature: str,
    ranked_results: list[dict],
    db_path: str | Path | None = None,
) -> int:
    init_database(db_path)
    connection = get_connection(db_path)
    try:
        saved_count = 0
        now = _now_iso()
        for result in ranked_results:
            scholarship_name = result.get("scholarship_name")
            source_url = result.get("source_url") or result.get("display_link")
            if not scholarship_name or not source_url:
                continue
            scholarship_key = build_scholarship_hash(
                str(scholarship_name),
                str(source_url),
            )
            payload = (
                profile_signature,
                scholarship_key,
                scholarship_name,
                result.get("compatibility_score"),
                result.get("compatibility_points"),
                result.get("max_possible_points"),
                json.dumps(result.get("matched_profile_fields", []), ensure_ascii=False),
                json.dumps(result.get("missing_profile_fields", []), ensure_ascii=False),
                result.get("source_trust_score"),
                result.get("deadline_status"),
                result.get("display_link"),
                result.get("source_url"),
                result.get("official_link"),
                result.get("application_url"),
                result.get("pdf_url"),
                result.get("final_score"),
                result.get("priority_label"),
                now,
            )
            connection.execute(
                """
                INSERT INTO ranking_records (
                    profile_signature, scholarship_key, scholarship_name,
                    compatibility_score, compatibility_points, max_possible_points,
                    matched_profile_fields_json, missing_profile_fields_json,
                    source_trust_score, deadline_status, display_link, source_url,
                    official_link, application_url, pdf_url, final_score,
                    priority_label, last_checked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_signature, scholarship_key) DO UPDATE SET
                    scholarship_name = excluded.scholarship_name,
                    compatibility_score = excluded.compatibility_score,
                    compatibility_points = excluded.compatibility_points,
                    max_possible_points = excluded.max_possible_points,
                    matched_profile_fields_json = excluded.matched_profile_fields_json,
                    missing_profile_fields_json = excluded.missing_profile_fields_json,
                    source_trust_score = excluded.source_trust_score,
                    deadline_status = excluded.deadline_status,
                    display_link = excluded.display_link,
                    source_url = excluded.source_url,
                    official_link = excluded.official_link,
                    application_url = excluded.application_url,
                    pdf_url = excluded.pdf_url,
                    final_score = excluded.final_score,
                    priority_label = excluded.priority_label,
                    last_checked_at = excluded.last_checked_at
                """,
                payload,
            )
            saved_count += 1
        connection.commit()
        return saved_count
    finally:
        close_connection(connection)


def list_ranking_records(
    profile_signature: str,
    db_path: str | Path | None = None,
) -> list[dict]:
    init_database(db_path)
    connection = get_connection(db_path)
    try:
        rows = connection.execute(
            """
            SELECT * FROM ranking_records
            WHERE profile_signature = ?
            ORDER BY final_score DESC, compatibility_score DESC, source_trust_score DESC,
                     scholarship_name ASC
            """,
            (profile_signature,),
        ).fetchall()
        records: list[dict] = []
        for row in rows:
            record = dict(row)
            for key in ("matched_profile_fields_json", "missing_profile_fields_json"):
                try:
                    record[key.removesuffix("_json")] = json.loads(record.get(key) or "[]")
                except json.JSONDecodeError:
                    record[key.removesuffix("_json")] = []
            records.append(record)
        return records
    finally:
        close_connection(connection)


def get_existing_scholarship_by_hash(
    scholarship_hash: str,
    db_path: str | Path | None = None,
    connection=None,
):
    owns_connection = connection is None
    connection = connection or get_connection(db_path)
    try:
        row = connection.execute(
            "SELECT * FROM scholarships WHERE scholarship_hash = ?",
            (scholarship_hash,),
        ).fetchone()
        return dict(row) if row is not None else None
    finally:
        if owns_connection:
            close_connection(connection)


def list_recent_scholarships(
    limit: int = 20, db_path: str | Path | None = None
) -> list[dict]:
    connection = get_connection(db_path)
    try:
        rows = connection.execute(
            """
            SELECT * FROM scholarships
            ORDER BY last_seen_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        close_connection(connection)


def list_scholarships_for_refresh(
    limit: int,
    stale_days: int,
    skip_closed: bool = True,
    db_path: str | Path | None = None,
) -> list[dict]:
    connection = get_connection(db_path)
    try:
        stale_modifier = f"-{max(0, int(stale_days))} days"
        rows = connection.execute(
            """
            SELECT * FROM scholarships
            ORDER BY
                CASE
                    WHEN last_seen_at IS NULL
                         OR datetime(last_seen_at) <= datetime('now', ?)
                    THEN 0 ELSE 1
                END,
                last_seen_at ASC
            LIMIT ?
            """,
            (stale_modifier, limit),
        ).fetchall()

        scholarships: list[dict] = []
        for row in rows:
            scholarship = dict(row)
            last_seen_at = scholarship.get("last_seen_at")
            scholarship["is_stale"] = (
                last_seen_at is None
                or connection.execute(
                    "SELECT CASE WHEN datetime(?) <= datetime('now', ?) THEN 1 ELSE 0 END AS is_stale",
                    (last_seen_at, stale_modifier),
                ).fetchone()["is_stale"]
                == 1
            )
            scholarship["skip_closed"] = bool(skip_closed)
            scholarships.append(scholarship)
        return scholarships
    finally:
        close_connection(connection)


def update_scholarship_refresh_status(
    scholarship_hash: str,
    application_status: str | None = None,
    deadline: str | None = None,
    db_path: str | Path | None = None,
) -> None:
    connection = get_connection(db_path)
    try:
        connection.execute(
            """
            UPDATE scholarships
            SET application_status = COALESCE(?, application_status),
                deadline = COALESCE(?, deadline),
                updated_at = ?,
                last_seen_at = ?
            WHERE scholarship_hash = ?
            """,
            (
                application_status,
                deadline,
                _now_iso(),
                _now_iso(),
                scholarship_hash,
            ),
        )
        connection.commit()
    finally:
        close_connection(connection)


def update_scholarship_last_seen(
    scholarship_hash: str,
    db_path: str | Path | None = None,
) -> None:
    connection = get_connection(db_path)
    try:
        connection.execute(
            """
            UPDATE scholarships
            SET last_seen_at = ?, updated_at = ?
            WHERE scholarship_hash = ?
            """,
            (_now_iso(), _now_iso(), scholarship_hash),
        )
        connection.commit()
    finally:
        close_connection(connection)
