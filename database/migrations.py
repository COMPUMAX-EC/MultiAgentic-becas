from __future__ import annotations

from pathlib import Path

from database.connection import close_connection, get_connection
from database.models import CREATE_TABLE_STATEMENTS


def run_migrations(db_path: str | Path | None = None) -> None:
    connection = get_connection(db_path)
    try:
        cursor = connection.cursor()
        for statement in CREATE_TABLE_STATEMENTS:
            cursor.execute(statement)
        connection.commit()
    finally:
        close_connection(connection)
