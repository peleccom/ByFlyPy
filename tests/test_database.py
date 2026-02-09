"""Tests for ByFlyPy database module."""

import os
import tempfile

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


class TestDBManager:
    """Test DBManager class for database operations."""

    FILENAME = ":memory:"

    def setup_method(self):
        """Set up test fixtures."""
        self._table = Table(self.FILENAME)
        self.db_manager = DBManager(self._table)

    def teardown_method(self):
        """Clean up after tests."""
        self._table.close()
        self._table = None
        self.db_manager = None

    def test_save_password(self):
        """Test saving password to database."""
        self.db_manager.save_password("user1", "pass123")
        result = self.db_manager.get_password("user1")
        assert result is not None
        assert result[0] == "user1"
        assert result[1] == "pass123"

    def test_update_password(self):
        """Test updating existing password."""
        self.db_manager.save_password("user1", "pass123")
        self.db_manager.save_password("user1", "newpass")
        result = self.db_manager.get_password("user1")
        assert result[1] == "newpass"

    def test_get_password_non_existent(self):
        """Test getting password for non-existent user."""
        result = self.db_manager.get_password("nonexistent")
        assert result is None

    def test_delete_password(self):
        """Test deleting password from database."""
        self.db_manager.save_password("user1", "pass123")
        assert self.db_manager.delete_password("user1") is True
        assert self.db_manager.get_password("user1") is None

    def test_delete_non_existent(self):
        """Test deleting non-existent password."""
        assert self.db_manager.delete_password("nonexistent") is False


class TestTable:
    """Test Table class for database operations."""

    FILENAME = ":memory:"

    def setup_method(self):
        """Set up test fixtures."""
        self._table = Table(self.FILENAME)

    def teardown_method(self):
        """Clean up after tests."""
        self._table.close()
        self._table = None

    def test_create_table(self):
        """Test table creation."""
        assert self._table.db_filename == ":memory:"

    def test_execute_query(self):
        """Test executing a query."""
        self._table.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
        self._table.execute("INSERT INTO test (id) VALUES (1)")
        cursor = self._table.execute("SELECT id FROM test")
        result = cursor.fetchone()
        assert result[0] == 1

    def test_commit(self):
        """Test commit functionality."""
        self._table.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
        self._table.execute("INSERT INTO test (id) VALUES (1)")
        self._table.commit()
        cursor = self._table.execute("SELECT id FROM test")
        assert cursor.fetchone() is not None

    def test_close(self):
        """Test close functionality."""
        self._table.close()
        assert self._table._connection is None

    def test_list(self):
        """Test listing all records."""
        self._table.create_table_if_not_exists()
        self._table.add(Record("user1", "pass1"))
        self._table.add(Record("user2", "pass2"))
        records = self._table.list()
        assert len(records) == 2

    def test_add(self):
        """Test adding a record to the table."""
        self._table.create_table_if_not_exists()
        assert len(self._table.list()) == 0
        record = Record("a", "b")
        self._table.add(record)
        assert len(self._table.list()) == 1

    def test_get(self):
        """Test getting a record by primary key."""
        self._table.create_table_if_not_exists()
        self._table.add(Record("user1", "pass1"))
        record = self._table.get("user1")
        assert record is not None
        assert record.pk == "user1"
        assert record.password == "pass1"

    def test_get_non_exists(self):
        """Test getting a non-existent record."""
        self._table.create_table_if_not_exists()
        record = self._table.get("nonexistent")
        assert record is None

    def test_delete(self):
        """Test deleting a record from the table."""
        self._table.create_table_if_not_exists()
        self._table.add(Record("user1", "pass1"))
        assert len(self._table.list()) == 1
        self._table.delete("user1")
        assert len(self._table.list()) == 0


class TestDatabaseIntegration:
    """Integration tests for database with real file."""

    DB_FILENAME = "test_byflypy.db"

    def setup_method(self):
        """Set up test fixtures."""
        if os.path.exists(self.DB_FILENAME):
            os.remove(self.DB_FILENAME)

    def teardown_method(self):
        """Clean up after tests."""
        if os.path.exists(self.DB_FILENAME):
            os.remove(self.DB_FILENAME)

    def test_save_and_retrieve_multiple(self):
        """Test saving and retrieving multiple credentials."""
        with Table(self.DB_FILENAME) as table:
            db_manager = DBManager(table)
            db_manager.save_password("user1", "pass1")
            db_manager.save_password("user2", "pass2")
            db_manager.save_password("user3", "pass3")

            assert db_manager.get_password("user1")[1] == "pass1"
            assert db_manager.get_password("user2")[1] == "pass2"
            assert db_manager.get_password("user3")[1] == "pass3"

    def test_file_based_operations(self):
        """Test database operations with actual file."""
        with Table(self.DB_FILENAME) as table:
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
