"""Tests for TokenManager."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from byflypy.clients.api_client import TokenManager


class TestTokenManagerLoad:
    """Test TokenManager.load() method."""

    def test_load_no_file(self):
        """Test loading when token file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / "token.json"
            manager = TokenManager(token_file=token_file)

            result = manager.load("+375291234567")

            assert result is None

    def test_load_file_not_exists_default_path(self):
        """Test loading with default path when file doesn't exist."""
        with patch("byflypy.clients.api_client.Path.exists", return_value=False):
            manager = TokenManager(token_file=Path("/nonexistent/token.json"))
            result = manager.load("+375291234567")
            assert result is None

    def test_load_phone_not_in_file(self):
        """Test loading when phone number not in token file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / "token.json"
            token_file.write_text(json.dumps({"+375299876543": {"access_token": "token123"}}))

            manager = TokenManager(token_file=token_file)
            result = manager.load("+375291234567")

            assert result is None

    def test_load_no_access_token(self):
        """Test loading when access_token is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / "token.json"
            token_file.write_text(json.dumps({"+375291234567": {"phone": "+375291234567"}}))

            manager = TokenManager(token_file=token_file)
            result = manager.load("+375291234567")

            assert result is None

    def test_load_valid_token_no_expiry(self):
        """Test loading valid token without expiry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / "token.json"
            token_data = {
                "+375291234567": {
                    "access_token": "test_token_abc123",
                    "expires_at": None,
                    "phone": "+375291234567",
                }
            }
            token_file.write_text(json.dumps(token_data))

            manager = TokenManager(token_file=token_file)
            result = manager.load("+375291234567")

            assert result == "test_token_abc123"

    def test_load_valid_token_with_expiry_not_expired(self):
        """Test loading valid token that hasn't expired."""
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / "token.json"
            future_date = (datetime.now() + timedelta(days=1)).isoformat()
            token_data = {
                "+375291234567": {
                    "access_token": "test_token_xyz789",
                    "expires_at": future_date,
                    "phone": "+375291234567",
                }
            }
            token_file.write_text(json.dumps(token_data))

            manager = TokenManager(token_file=token_file)
            result = manager.load("+375291234567")

            assert result == "test_token_xyz789"

    def test_load_expired_token(self, capsys):
        """Test loading expired token."""
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / "token.json"
            past_date = (datetime.now() - timedelta(days=1)).isoformat()
            token_data = {
                "+375291234567": {
                    "access_token": "expired_token",
                    "expires_at": past_date,
                    "phone": "+375291234567",
                }
            }
            token_file.write_text(json.dumps(token_data))

            manager = TokenManager(token_file=token_file)
            result = manager.load("+375291234567")

            assert result is None
            captured = capsys.readouterr()
            assert "has expired" in captured.out

    def test_load_invalid_json(self):
        """Test loading with invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / "token.json"
            token_file.write_text("invalid json content")

            manager = TokenManager(token_file=token_file)
            result = manager.load("+375291234567")

            assert result is None

    def test_load_invalid_date_format(self):
        """Test loading with invalid date format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / "token.json"
            token_data = {
                "+375291234567": {
                    "access_token": "token",
                    "expires_at": "not-a-date",
                    "phone": "+375291234567",
                }
            }
            token_file.write_text(json.dumps(token_data))

            manager = TokenManager(token_file=token_file)
            result = manager.load("+375291234567")

            assert result is None


class TestTokenManagerSave:
    """Test TokenManager.save() method."""

    def test_save_new_file(self, capsys):
        """Test saving token to new file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / "token.json"
            manager = TokenManager(token_file=token_file)

            manager.save("+375291234567", "new_token_abc", None)

            assert token_file.exists()
            data = json.loads(token_file.read_text())
            assert data["+375291234567"]["access_token"] == "new_token_abc"
            assert data["+375291234567"]["expires_at"] is None
            captured = capsys.readouterr()
            assert "Token saved" in captured.out

    def test_save_new_file_with_expiry(self):
        """Test saving token with expiry date."""
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / "token.json"
            manager = TokenManager(token_file=token_file)
            expires_at = datetime(2025, 12, 31, 23, 59, 59)

            manager.save("+375291234567", "token_with_expiry", expires_at)

            data = json.loads(token_file.read_text())
            assert data["+375291234567"]["access_token"] == "token_with_expiry"
            assert "2025-12-31" in data["+375291234567"]["expires_at"]

    def test_save_to_existing_file(self):
        """Test saving token to existing file with other tokens."""
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / "token.json"
            existing_data = {
                "+375299876543": {
                    "access_token": "existing_token",
                    "expires_at": None,
                    "phone": "+375299876543",
                }
            }
            token_file.write_text(json.dumps(existing_data))

            manager = TokenManager(token_file=token_file)
            manager.save("+375291234567", "new_token", None)

            data = json.loads(token_file.read_text())
            assert len(data) == 2
            assert data["+375299876543"]["access_token"] == "existing_token"
            assert data["+375291234567"]["access_token"] == "new_token"

    def test_save_overwrites_existing_phone(self):
        """Test saving overwrites token for same phone number."""
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / "token.json"
            token_data = {
                "+375291234567": {
                    "access_token": "old_token",
                    "expires_at": None,
                    "phone": "+375291234567",
                }
            }
            token_file.write_text(json.dumps(token_data))

            manager = TokenManager(token_file=token_file)
            manager.save("+375291234567", "updated_token", None)

            data = json.loads(token_file.read_text())
            assert len(data) == 1
            assert data["+375291234567"]["access_token"] == "updated_token"

    def test_save_invalid_json_in_existing_file(self):
        """Test saving when existing file has invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / "token.json"
            token_file.write_text("invalid json")

            manager = TokenManager(token_file=token_file)
            manager.save("+375291234567", "new_token", None)

            data = json.loads(token_file.read_text())
            assert data["+375291234567"]["access_token"] == "new_token"


class TestTokenManagerMocks:
    """Test mocks for TokenManager."""

    def test_mock_token_manager_load(self):
        """Test using mock TokenManager for load."""
        mock_manager = Mock(spec=TokenManager)
        mock_manager.load.return_value = "mocked_token"

        result = mock_manager.load("+375291234567")

        assert result == "mocked_token"
        mock_manager.load.assert_called_once_with("+375291234567")

    def test_mock_token_manager_save(self):
        """Test using mock TokenManager for save."""
        mock_manager = Mock(spec=TokenManager)

        mock_manager.save("+375291234567", "test_token", None)

        mock_manager.save.assert_called_once_with("+375291234567", "test_token", None)

    def test_mock_token_manager_multiple_phones(self):
        """Test mock with multiple phone numbers."""
        mock_manager = Mock(spec=TokenManager)
        mock_manager.load.side_effect = ["token1", "token2", None]

        assert mock_manager.load("phone1") == "token1"
        assert mock_manager.load("phone2") == "token2"
        assert mock_manager.load("phone3") is None
