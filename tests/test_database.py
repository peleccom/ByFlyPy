"""Tests for ByFlyPy database module."""

import os
import tempfile

import pytest

from byflypy import html_client
from byflypy.database import DBManager, Record, Table
from byflypy.html_client import log_to_file


class TestRecord:
    """Test Record dataclass."""

    def test_record_creation(self):
        """Test creating a Record object."""
        record = Record("login", "password", "notes")
        assert record.pk == "login"
        assert record.password == "password"
        assert record.notes == "notes"

    def test_record_repr(self):
        """Test Record string representation."""
        record = Record("test", "pass", "")
        assert "test" in repr(record)


@pytest.fixture
def table():
    """Provide a Table instance for tests."""
    _table = Table(":memory:")
    yield _table
    _table.close()


@pytest.fixture
def db_manager(table):
    """Provide a DBManager instance for tests."""
    return DBManager(table)


class TestDBManager:
    """Test DBManager class for database operations."""

    def test_save_password(self, db_manager):
        """Test saving password to database."""
        db_manager.save_password("user1", "pass123")
        result = db_manager.get_password("user1")
        assert result is not None
        assert result[0] == "user1"
        assert result[1] == "pass123"

    def test_update_password(self, db_manager):
        """Test updating existing password."""
        db_manager.save_password("user1", "pass123")
        db_manager.save_password("user1", "newpass")
        result = db_manager.get_password("user1")
        assert result[1] == "newpass"

    def test_get_password_non_existent(self, db_manager):
        """Test getting password for non-existent user."""
        result = db_manager.get_password("nonexistent")
        assert result is None

    def test_delete_password(self, db_manager):
        """Test deleting password from database."""
        db_manager.save_password("user1", "pass123")
        assert db_manager.delete_password("user1") is True
        assert db_manager.get_password("user1") is None

    def test_delete_non_existent(self, db_manager):
        """Test deleting non-existent password."""
        assert db_manager.delete_password("nonexistent") is False


class TestTable:
    """Test Table class for database operations."""

    def test_create_table(self, table):
        """Test table creation."""
        assert table.db_filename == ":memory:"

    def test_execute_query(self, table):
        """Test executing a query."""
        table.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
        table.execute("INSERT INTO test (id) VALUES (1)")
        cursor = table.execute("SELECT id FROM test")
        result = cursor.fetchone()
        assert result[0] == 1

    def test_commit(self, table):
        """Test commit functionality."""
        table.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
        table.execute("INSERT INTO test (id) VALUES (1)")
        table.commit()
        cursor = table.execute("SELECT id FROM test")
        assert cursor.fetchone() is not None

    def test_close(self, table):
        """Test close functionality."""
        table.close()
        assert table._connection is None

    def test_list(self, table):
        """Test listing all records."""
        table.create_table_if_not_exists()
        table.add(Record("user1", "pass1"))
        table.add(Record("user2", "pass2"))
        records = table.list()
        assert len(records) == 2

    def test_add(self, table):
        """Test adding a record to the table."""
        table.create_table_if_not_exists()
        assert len(table.list()) == 0
        record = Record("a", "b")
        table.add(record)
        assert len(table.list()) == 1

    def test_get(self, table):
        """Test getting a record by primary key."""
        table.create_table_if_not_exists()
        table.add(Record("user1", "pass1"))
        record = table.get("user1")
        assert record is not None
        assert record.pk == "user1"
        assert record.password == "pass1"

    def test_get_non_exists(self, table):
        """Test getting a non-existent record."""
        table.create_table_if_not_exists()
        record = table.get("nonexistent")
        assert record is None

    def test_delete(self, table):
        """Test deleting a record from the table."""
        table.create_table_if_not_exists()
        table.add(Record("user1", "pass1"))
        assert len(table.list()) == 1
        table.delete("user1")
        assert len(table.list()) == 0


@pytest.fixture
def db_filename():
    """Provide a temporary database filename."""
    filename = "test_byflypy.db"
    yield filename
    if os.path.exists(filename):
        os.remove(filename)


class TestDatabaseIntegration:
    """Integration tests for database with real file."""

    def test_save_and_retrieve_multiple(self, db_filename):
        """Test saving and retrieving multiple credentials."""
        with Table(db_filename) as table:
            db_manager = DBManager(table)
            db_manager.save_password("user1", "pass1")
            db_manager.save_password("user2", "pass2")
            db_manager.save_password("user3", "pass3")

            assert db_manager.get_password("user1")[1] == "pass1"
            assert db_manager.get_password("user2")[1] == "pass2"
            assert db_manager.get_password("user3")[1] == "pass3"

    def test_file_based_operations(self, db_filename):
        """Test database operations with actual file."""
        with Table(db_filename) as table:
            table.create_table_if_not_exists()

            record = Record("testuser", "testpass")
            table.add(record)

            assert len(table.list()) == 1
            retrieved = table.get("testuser")
            assert retrieved is not None
            assert retrieved.pk == "testuser"

            table.delete("testuser")
            assert len(table.list()) == 0


class TestLogToFile:
    """Test log_to_file function from html_client module."""

    def test_log_to_file(self):
        """Test logging content to file."""
        CONTENT = "test"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as f:
            filename = f.name
        try:
            log_to_file(filename, CONTENT)
            assert os.path.getsize(filename) == 0
            log_to_file(filename, CONTENT, force=True)
            assert os.path.getsize(filename) == len(CONTENT)
        finally:
            if os.path.exists(filename):
                os.remove(filename)

    def test_log_if_debug(self):
        """Test logging when debug mode is enabled."""
        CONTENT = "test"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as f:
            filename = f.name
        try:
            html_client._DEBUG_ = True
            log_to_file(filename, CONTENT)
            assert os.path.getsize(filename) == len(CONTENT)
        finally:
            if os.path.exists(filename):
                os.remove(filename)
            html_client._DEBUG_ = False
