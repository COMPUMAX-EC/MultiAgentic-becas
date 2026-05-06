from __future__ import annotations

import sqlite3
from pathlib import Path

from config.settings import settings


def resolve_database_path(db_path: str | Path | None = None) -> Path:
    resolved_path = Path(db_path) if db_path is not None else settings.DATABASE_PATH
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    return resolved_path


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    database_path = resolve_database_path(db_path)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def close_connection(connection: sqlite3.Connection | None) -> None:
    if connection is not None:
        connection.close()
