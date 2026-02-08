"""Database module for storing credentials."""

from __future__ import annotations

import sqlite3
from typing import Optional


class Table:
    """SQLite table wrapper."""

    def __init__(self, db_filename: str) -> None:
        self.db_filename = db_filename
        self._connection: Optional[sqlite3.Connection] = None

    def _get_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_filename)
        return self._connection

    def execute(self, query: str, parameters: tuple = ()) -> sqlite3.Cursor:
        conn = self._get_connection()
        return conn.execute(query, parameters)

    def commit(self) -> None:
        if self._connection:
            self._connection.commit()

    def close(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None


class DBManager:
    """Database manager for user credentials."""

    TABLE_NAME = "users"

    def __init__(self, table: Table) -> None:
        self._table = table
        self._create_table()

    def _create_table(self) -> None:
        """Create users table if not exists."""
        query = f"""
            CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                login TEXT PRIMARY KEY,
                password TEXT NOT NULL
            )
        """
        self._table.execute(query)
        self._table.commit()

    def save_password(self, login: str, password: str) -> None:
        """Save or update password for login."""
        query = f"""
            INSERT OR REPLACE INTO {self.TABLE_NAME} (login, password)
            VALUES (?, ?)
        """
        self._table.execute(query, (login, password))
        self._table.commit()

    def get_password(self, login: str) -> Optional[tuple[str, str]]:
        """Get password for login."""
        query = f"SELECT login, password FROM {self.TABLE_NAME} WHERE login = ?"
        cursor = self._table.execute(query, (login,))
        result = cursor.fetchone()
        if result:
            return (result[0], result[1])
        return None

    def delete_password(self, login: str) -> bool:
        """Delete password for login."""
        query = f"DELETE FROM {self.TABLE_NAME} WHERE login = ?"
        cursor = self._table.execute(query, (login,))
        self._table.commit()
        return cursor.rowcount > 0
