"""Database module for storing credentials."""

from __future__ import annotations

import sqlite3


class ErrorDatabase(Exception):
    """Database error exception."""


class Record:
    """Database record for storing login credentials."""

    def __init__(self, pk: str, password: str, notes: str = "") -> None:
        self.pk = pk
        self.password = password
        self.notes = notes

    def __repr__(self) -> str:
        return f"Record<{self.pk}>"


class Table:
    """SQLite table wrapper."""

    def __init__(self, db_filename: str) -> None:
        self.db_filename = db_filename
        self._connection: sqlite3.Connection | None = None

    def _get_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_filename)
        return self._connection

    def _connect(self) -> sqlite3.Connection:
        """Alias for _get_connection for backwards compatibility."""
        return self._get_connection()

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

    def create_table_if_not_exists(self) -> None:
        """Create the users table if it doesn't exist."""
        query = """
            CREATE TABLE IF NOT EXISTS users (
                login TEXT PRIMARY KEY,
                password TEXT NOT NULL
            )
        """
        self.execute(query)
        self.commit()

    def list(self) -> list[Record]:
        """List all records in the table."""
        query = "SELECT login, password FROM users"
        cursor = self.execute(query)
        return [Record(row[0], row[1]) for row in cursor.fetchall()]

    def add(self, record: Record) -> Record:
        """Add a record to the table."""
        query = "INSERT OR IGNORE INTO users (login, password) VALUES (?, ?)"
        self.execute(query, (record.pk, record.password))
        self.commit()
        return record

    def get(self, pk: str) -> Record | None:
        """Get a record by primary key."""
        query = "SELECT login, password FROM users WHERE login = ?"
        cursor = self.execute(query, (pk,))
        result = cursor.fetchone()
        if result:
            return Record(result[0], result[1])
        return None

    def delete(self, pk: str) -> None:
        """Delete a record by primary key."""
        query = "DELETE FROM users WHERE login = ?"
        self.execute(query, (pk,))
        self.commit()


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

    def get_password(self, login: str) -> tuple[str, str | None] | None:
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
