from __future__ import annotations

from pathlib import Path

from database.connection import close_connection, get_connection
from database.models import CREATE_TABLE_STATEMENTS


def _apply_schema_upgrades(connection) -> None:
    """Lightweight column adds for existing SQLite databases."""
    user_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(users)").fetchall()
    }
    if "profile_json" not in user_columns:
        connection.execute("ALTER TABLE users ADD COLUMN profile_json TEXT")
    if "role" not in user_columns:
        connection.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    if "premium_status" not in user_columns:
        connection.execute("ALTER TABLE users ADD COLUMN premium_status TEXT DEFAULT 'none'")
    if "premium_receipt_path" not in user_columns:
        connection.execute("ALTER TABLE users ADD COLUMN premium_receipt_path TEXT")
    if "is_premium" not in user_columns:
        connection.execute("ALTER TABLE users ADD COLUMN is_premium INTEGER DEFAULT 0")


def run_migrations(db_path: str | Path | None = None) -> None:
    connection = get_connection(db_path)
    try:
        cursor = connection.cursor()
        for statement in CREATE_TABLE_STATEMENTS:
            cursor.execute(statement)
        _apply_schema_upgrades(connection)
        connection.commit()
    finally:
        close_connection(connection)
