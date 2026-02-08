"""Tests for ByFlyPy CLI."""

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from byflypy.cli import (
    UI,
    Program,
    print_traffic_table,
)
from byflypy.models import TrafficDetails, UserInfo


class TestPrintTrafficTable:
    """Test print_traffic_table function."""

    def test_print_traffic_table(self, capsys):
        """Test printing traffic table."""
        traffic = TrafficDetails(
            total_incoming=Decimal("119233.25"),
            total_outgoing=Decimal("20872.50"),
            total_traffic=Decimal("140105.75"),
            total_duration="181:47:47",
            sessions=[],
        )

        print_traffic_table(traffic)
        captured = capsys.readouterr()

        assert "Traffic Statistics" in captured.out
        assert "119233.25" in captured.out
        assert "20872.50" in captured.out
        assert "140105.75" in captured.out
        assert "181:47:47" in captured.out


class TestUIHtmlClient:
    """Test UI class with HTML client."""

    @pytest.fixture
    def mock_html_client(self):
        """Create a mock HTML client."""
        # Use regular Mock without spec to allow flexible attribute access
        client = Mock()
        client.__class__.__name__ = "ByFlyHtmlClient"
        client.info = "Test Info"
        return client

    @pytest.fixture
    def ui_html(self, mock_html_client):
        """Create UI with HTML client."""
        return UI(mock_html_client)

    def test_print_info_html(self, ui_html, mock_html_client):
        """Test print_info with HTML client."""
        mock_html_client.get_account_info_page.return_value = UserInfo(
            full_name="Иванов Иван",
            plan="ЯСНА 100",
            balance=Decimal("100.50"),
        )
        mock_html_client.get_money_measure.return_value = "руб"

        result = ui_html.print_info()
        assert result is True

    def test_print_info_html_only_balance(self, ui_html, mock_html_client, capsys):
        """Test print_info with only balance."""
        mock_html_client.get_account_info_page.return_value = UserInfo(
            full_name="Иванов Иван",
            plan="ЯСНА 100",
            balance=Decimal("100.50"),
        )

        result = ui_html.print_info(only_balance=True)
        captured = capsys.readouterr()

        assert result is True
        assert "100.50" in captured.out

    def test_print_info_html_failure(self, ui_html, mock_html_client):
        """Test print_info failure with HTML client."""
        mock_html_client.get_account_info_page.return_value = None
        result = ui_html.print_info()
        assert result is False


class TestUIApiClient:
    """Test UI class with API client."""

    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client."""
        # Use regular Mock without spec to allow flexible attribute access
        client = Mock()
        client.__class__.__name__ = "ByFlyApiClient"
        return client

    @pytest.fixture
    def ui_api(self, mock_api_client):
        """Create UI with API client."""
        return UI(mock_api_client)

    def test_print_info_api(self, ui_api, mock_api_client):
        """Test print_info with API client."""
        mock_contract = Mock()
        mock_contract.name = "Иванов Иван"
        mock_contract.balance = Decimal("47.49")
        mock_contract.terminate_in = 34

        mock_app = Mock()
        mock_app.tariff = Mock()
        mock_app.tariff.name = "ЯСНА 100"
        mock_contract.applications = [mock_app]

        mock_api_client.get_primary_contract.return_value = mock_contract

        result = ui_api.print_info()
        assert result is True

    def test_print_info_api_only_balance(self, ui_api, mock_api_client, capsys):
        """Test print_info with only balance for API client."""
        mock_contract = Mock()
        mock_contract.balance = Decimal("47.49")
        mock_contract.applications = []

        mock_api_client.get_primary_contract.return_value = mock_contract

        result = ui_api.print_info(only_balance=True)
        captured = capsys.readouterr()

        assert result is True
        assert "47.49" in captured.out

    def test_print_additional_info_api(self, ui_api, mock_api_client, capsys):
        """Test print_additional_info with API client."""
        mock_contract = Mock()
        mock_contract.id = 123
        mock_contract.applications = [Mock(id=456)]

        mock_traffic = TrafficDetails(
            total_incoming=Decimal("100.0"),
            total_outgoing=Decimal("50.0"),
            total_traffic=Decimal("150.0"),
            total_duration="10:00:00",
            sessions=[],
        )

        mock_api_client.get_primary_contract.return_value = mock_contract
        mock_api_client.get_traffic_details.return_value = mock_traffic

        result = ui_api.print_additional_info()
        captured = capsys.readouterr()

        assert result is True
        assert "Traffic Statistics" in captured.out


class TestProgram:
    """Test Program class."""

    @pytest.fixture
    def program(self):
        """Create a Program instance."""
        return Program()

    @pytest.fixture
    def mock_args_api_v1(self):
        """Create mock args for API v1."""
        args = Mock()
        args.use_api_v1 = True
        args.login = "test_login"
        args.password = "test_pass"
        args.quiet = False
        args.graph = None
        args.previous_period = False
        return args

    @pytest.fixture
    def mock_args_api_v2(self):
        """Create mock args for API v2."""
        args = Mock()
        args.use_api_v1 = False
        args.account_phone = "375331234567"
        args.account_password = "test_pass"
        args.access_token = None
        args.internet_login = None
        args.contract_id = None
        args.sms_code = None
        args.quiet = False
        args.graph = None
        args.previous_period = False
        return args

    @patch("byflypy.cli.ByFlyHtmlClient")
    def test_ui_api_v1(self, mock_client_class, program, mock_args_api_v1):
        """Test UI with API v1."""
        mock_client = Mock()
        mock_client.__class__.__name__ = "ByFlyHtmlClient"
        mock_client.login.return_value = True
        mock_client.get_account_info_page.return_value = UserInfo(
            full_name="Test User",
            plan="Test Plan",
            balance=Decimal("100.00"),
        )
        mock_client.get_money_measure.return_value = "руб"
        mock_client.get_payments_page.return_value = []
        mock_client.get_additional_info.return_value = None
        mock_client_class.return_value = mock_client

        result = program.ui(mock_args_api_v1)
        assert result == 0

    @patch("byflypy.cli.ByFlyApiClient")
    def test_ui_api_v2(self, mock_client_class, program, mock_args_api_v2):
        """Test UI with API v2."""
        mock_client = Mock()
        mock_client.__class__.__name__ = "ByFlyApiClient"
        mock_client.login.return_value = True
        mock_client.access_token = "test_token"

        mock_contract = Mock()
        mock_contract.name = "Test User"
        mock_contract.balance = Decimal("47.49")
        mock_contract.applications = []

        mock_client.get_primary_contract.return_value = mock_contract
        mock_client.get_internet_logins.return_value = [
            {"login": "test", "application_id": 1, "tariff_name": "ЯСНА 100"}
        ]
        mock_client.get_traffic_details.return_value = None

        mock_client_class.return_value = mock_client

        result = program.ui(mock_args_api_v2)
        assert result == 0

    @patch("byflypy.cli.ByFlyApiClient")
    def test_ui_api_v2_multiple_logins_error(self, mock_client_class, program, mock_args_api_v2):
        """Test UI with API v2 when multiple logins exist."""
        mock_client = Mock()
        mock_client.__class__.__name__ = "ByFlyApiClient"
        mock_client.login.return_value = True
        mock_client.access_token = "test_token"

        mock_contract = Mock()
        mock_contract.id = 123
        mock_client.get_primary_contract.return_value = mock_contract
        mock_client.get_internet_logins.return_value = [
            {"login": "login1", "application_id": 1, "tariff_name": "ЯСНА 100"},
            {"login": "login2", "application_id": 2, "tariff_name": "ЯСНА 200"},
        ]

        mock_client_class.return_value = mock_client

        result = program.ui(mock_args_api_v2)
        assert result == 2


class TestArgumentParser:
    """Test argument parser setup."""

    @pytest.fixture
    def program(self):
        """Create a Program instance."""
        return Program()

    def test_parser_creation(self, program):
        """Test that parser is created correctly."""
        parser = program.setup_cmd_parser()
        assert parser is not None

    def test_api_v1_arguments(self, program):
        """Test API v1 argument parsing."""
        parser = program.setup_cmd_parser()
        args = parser.parse_args(["--api-v1", "-l", "test", "-p", "pass"])

        assert args.use_api_v1 is True
        assert args.login == "test"
        assert args.password == "pass"

    def test_api_v2_arguments(self, program):
        """Test API v2 argument parsing."""
        parser = program.setup_cmd_parser()
        args = parser.parse_args(
            [
                "--account-phone",
                "375331234567",
                "--account-password",
                "pass",
                "--internet-login",
                "mylogin",
            ]
        )

        assert args.account_phone == "375331234567"
        assert args.account_password == "pass"
        assert args.internet_login == "mylogin"

    def test_graph_arguments(self, program):
        """Test graph argument parsing."""
        parser = program.setup_cmd_parser()

        args = parser.parse_args(["-g", "time"])
        assert args.graph == "time"

        args = parser.parse_args(["-g", "traf"])
        assert args.graph == "traf"

    def test_quiet_mode(self, program):
        """Test quiet mode argument."""
        parser = program.setup_cmd_parser()
        args = parser.parse_args(["-q"])
        assert args.quiet is True

    def test_debug_mode(self, program):
        """Test debug mode argument."""
        parser = program.setup_cmd_parser()
        args = parser.parse_args(["-d"])
        assert args.debug is True
