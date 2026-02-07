"""Database module for managing user credentials."""

import getpass
import logging
import sqlite3
import sys
from typing import Optional

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Raised when database operations fail."""

    pass


class Record:
    """Represents a database record."""

    def __init__(
        self, login: str, password: str, alias: Optional[str] = None, pk: Optional[int] = None
    ) -> None:
        self._login = login
        self._password = password
        self._alias = alias
        self._pk = pk

    @classmethod
    def from_cursor_row(cls, row: sqlite3.Row) -> "Record":
        """Create Record from cursor row."""
        return cls(row["login"], row["pass"], row["alias"], pk=row["id"])

    @property
    def login(self) -> str:
        return self._login

    @property
    def password(self) -> str:
        return self._password

    @property
    def alias(self) -> Optional[str]:
        return self._alias

    @property
    def pk(self) -> Optional[int]:
        return self._pk

    def set_pk(self, pk: int) -> None:
        self._pk = pk


# Backwards compatibility alias
ErrorDatabase = DatabaseError


class Table:
    """Database table manager."""

    DEFAULT_DB_FILENAME = "users.db"
    SQL_CREATE_TABLE_QUERY = """CREATE TABLE IF NOT EXISTS USERS (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login CHAR(25),
        pass CHAR(25),
        alias CHAR(25)
    )"""
    SQL_INSERT_QUERY = "INSERT INTO USERS (login, pass, alias) VALUES (?, ?, ?)"
    SQL_LIST_QUERY = "SELECT * FROM USERS"
    SQL_DELETE_QUERY = "DELETE FROM USERS WHERE id = ?"
    SQL_GET_QUERY = "SELECT * FROM USERS WHERE login = ? OR alias = ?"

    def __init__(self, filename: str = DEFAULT_DB_FILENAME) -> None:
        try:
            self._connection = sqlite3.connect(filename)
            self.create_table_if_not_exists()
            self._connection.row_factory = sqlite3.Row
        except Exception as err:
            logging.exception(err)
            raise DatabaseError(f"Cannot open file {filename}") from err

    def close(self) -> None:
        """Close database connection."""
        if hasattr(self, "_connection"):
            self._connection.close()

    def __del__(self) -> None:
        self.close()

    def create_table_if_not_exists(self) -> None:
        """Create database table if it doesn't exist."""
        try:
            self._connection.execute(self.SQL_CREATE_TABLE_QUERY)
            self._connection.commit()
        except Exception as err:
            raise DatabaseError("Cannot create new table") from err

    def add(self, record: Record) -> Record:
        """Add new record to database.

        Args:
            record: Record to add

        Returns:
            Record with assigned pk

        Raises:
            DatabaseError: If insert fails
        """
        try:
            cursor = self._connection.execute(
                self.SQL_INSERT_QUERY, [record.login, record.password, record.alias]
            )
            self._connection.commit()
            record.set_pk(cursor.lastrowid)
            return record
        except Exception as err:
            raise DatabaseError("Cannot add record") from err

    def get(self, query: str) -> Optional[Record]:
        """Get record by login or alias.

        Args:
            query: Login or alias to search for

        Returns:
            Record if found, None otherwise
        """
        try:
            cursor = self._connection.cursor()
            cursor.execute(self.SQL_GET_QUERY, [query, query])
            row = cursor.fetchone()
            if row is not None:
                return Record.from_cursor_row(row)
        except Exception as err:
            logger.exception(err)
        return None

    def delete(self, pk: int) -> None:
        """Delete record by primary key.

        Args:
            pk: Primary key to delete

        Raises:
            DatabaseError: If delete fails
        """
        try:
            pk = int(pk)
            self._connection.execute(self.SQL_DELETE_QUERY, [pk])
        except Exception as err:
            logger.exception(err)
            raise DatabaseError("Cannot delete entry") from err

    def list(self) -> list[Record]:
        """List all records in database.

        Returns:
            List of all records
        """
        results = []
        cursor = self._connection.cursor()
        cursor.execute(self.SQL_LIST_QUERY)
        for row in cursor.fetchall():
            results.append(Record.from_cursor_row(row))
        return results


class DBManager:
    """Interface to access database with logins and passwords."""

    def __init__(self, table: Table) -> None:
        self._table = table

    def get_password(self, query: str) -> Optional[tuple[str, str]]:
        """Get password from entry with login or alias matching query.

        Args:
            query: Login or alias to search for

        Returns:
            Tuple of (login, password) or None if not found
        """
        record = self._table.get(query)
        if record:
            return record.login, record.password
        return None


def handle_interactive_mode(table: Table) -> None:  # pragma: no cover
    """Handle interactive database management mode."""
    print(
        """Manage database:
list     - list of entries
add      - add new entry
del <id> - delete entry by id
q        - quit
"""
    )
    while True:
        a = input(">>")
        if a == "list":
            print(f"{'id':5}|{'login':15}|{'password':15}|{'alias':15}|\n")
            for record in table.list():
                print(f"{record.pk:5}|{record.login:15}|{'*':15}|{record.alias:15}|")
        if a == "q":
            return
        if a == "add":
            try:
                login = input("login:")
                if not login:
                    continue
                password = getpass.getpass("password:")
                if not password:
                    continue
                alias = input("alias:")
                record = Record(login, password, alias)
                table.add(record)
            except Exception as err:
                logger.exception(err)
        if a.startswith("del "):
            _, _, pk = a.partition(" ")
            table.delete(pk)


def main() -> None:  # pragma: no cover
    """Main entry point for database CLI."""
    if len(sys.argv) == 1:
        print("database.py <database_filename>")
        sys.exit(1)

    try:
        table = Table(sys.argv[1])
        handle_interactive_mode(table)
    except DatabaseError as err:
        print(err)
        sys.exit(1)


if __name__ == "__main__":
    main()
