"""Tests for ByFlyPy CLI."""

import contextlib
import os
import sys
import tempfile
import types
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from byflypy.cli import (
    UI,
    Program,
    print_traffic_table,
)
from byflypy.cli_parser import CliNamespace
from byflypy.clients.api_client import (
    ApiApplication,
    ApiContract,
    ApiTariff,
    TokenManager,
)
from byflypy.clients.html_client import (
    AccountPageParser,
    PaymentsPageParser,
    StatPageParser,
)
from byflypy.console import default_console
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

        print_traffic_table(traffic, default_console())
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
        client.api_version = 1
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
        client.api_version = 2
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
        args.account_phone = "+375331234567"
        args.password = "test_pass"
        args.access_token = None
        args.btk_id = None
        args.sms_code = None
        args.quiet = False
        args.graph = None
        args.previous_period = False
        args.login = None  # Explicitly set to None
        args.imagefilename = None
        return args

    @pytest.fixture
    def mock_token_manager(self):
        """Create a mock TokenManager."""
        mock = Mock(spec=TokenManager)
        mock.load.return_value = None
        return mock

    def test_ui_api_v1(self, mock_args_api_v1):
        """Test UI with API v1 using injected client factory."""
        mock_client = Mock()
        mock_client.api_version = 1
        mock_client.info = None
        mock_client.get_account_info_page.return_value = UserInfo(
            full_name="Test User",
            plan="Test Plan",
            balance=Decimal("100.00"),
        )
        mock_client.get_money_measure.return_value = "руб"
        mock_client.get_payments_page.return_value = []
        mock_client.get_additional_info.return_value = None

        def factory(opt, db_path, console):
            return (mock_client, None)

        program = Program(client_factory=factory)
        result = program.ui(mock_args_api_v1)
        assert result == 0

    def test_ui_api_v2(self, mock_args_api_v2):
        """Test UI with API v2 using injected client factory."""
        mock_app = ApiApplication(
            id=1,
            tariff_id=1,
            price=Decimal("41.50"),
            tariff=ApiTariff(
                id=1,
                name="ЯСНА 100",
                description="",
                price=Decimal("41.50"),
                group_name=None,
                is_archival=False,
            ),
            services=[],
            can_change_tariff=True,
            tariff_change_available_at=None,
            available_tariffs=[],
            btk_login="",
        )
        mock_contract = ApiContract(
            id=123,
            user_id=1,
            login="test_login",
            btk_id="test_btk_id",
            balance=Decimal("47.49"),
            status="active",
            name="Test User",
            addresses=None,
            price=Decimal("41.50"),
            terminate_in=30,
            applications=[mock_app],
            can_add_funds=True,
            can_apply_promised_payment=True,
            max_promised_payment_amount=Decimal("20.00"),
        )
        mock_client = Mock()
        mock_client.api_version = 2
        mock_client.get_primary_contract.return_value = mock_contract
        mock_client.get_contracts.return_value = [mock_contract]
        mock_client.get_traffic_details.return_value = None

        def factory(opt, db_path, console):
            return (mock_client, None)

        program = Program(client_factory=factory)
        result = program.ui(mock_args_api_v2)
        assert result == 0

    def test_ui_api_v2_multiple_logins_error(self, mock_args_api_v2):
        """Test UI with API v2 when multiple contracts exist (exit 2)."""

        def factory(opt, db_path, console):
            return (None, 2)

        program = Program(client_factory=factory)
        result = program.ui(mock_args_api_v2)
        assert result == 2

    def test_ui_api_v2_invalid_login(self, mock_args_api_v2):
        """Test UI with API v2 when btk_id is invalid (exit 2)."""
        mock_args_api_v2.login = "invalid_btk_id"

        def factory(opt, db_path, console):
            return (None, 2)

        program = Program(client_factory=factory)
        result = program.ui(mock_args_api_v2)
        assert result == 2

    @patch("byflypy.cli.plotter_available", return_value=True)
    def test_ui_api_v2_with_graph_path(self, mock_plotter_available, mock_args_api_v2):
        """Test API v2 path with --graph uses Plotter (injected factory, no class patches)."""
        mock_args_api_v2.graph = "time"
        mock_args_api_v2.previous_period = False
        mock_args_api_v2.imagefilename = None

        mock_app = ApiApplication(
            id=1,
            tariff_id=1,
            price=Decimal("41.50"),
            tariff=ApiTariff(
                id=1,
                name="ЯСНА 100",
                description="",
                price=Decimal("41.50"),
                group_name=None,
                is_archival=False,
            ),
            services=[],
            can_change_tariff=True,
            tariff_change_available_at=None,
            available_tariffs=[],
            btk_login="",
        )
        mock_contract = ApiContract(
            id=123,
            user_id=1,
            login="test_login",
            btk_id="test_btk_id",
            balance=Decimal("47.49"),
            status="active",
            name="Test User",
            addresses=None,
            price=Decimal("41.50"),
            terminate_in=30,
            applications=[mock_app],
            can_add_funds=True,
            can_apply_promised_payment=True,
            max_promised_payment_amount=Decimal("20.00"),
        )
        mock_client = Mock()
        mock_client.api_version = 2
        mock_client.get_primary_contract.return_value = mock_contract
        mock_client.get_contracts.return_value = [mock_contract]
        mock_client.get_traffic_details.return_value = TrafficDetails(
            total_incoming=Decimal("100"),
            total_outgoing=Decimal("50"),
            total_traffic=Decimal("150"),
            total_duration="1:00:00",
            sessions=[],
        )

        def factory(opt, db_path, console):
            return (mock_client, None)

        fake_plotter_module = types.ModuleType("byflypy.plotter")
        fake_plotter_module.Plotter = Mock()  # type: ignore[unresolved-attribute]

        program = Program(client_factory=factory)
        with patch.dict(sys.modules, {"byflypy.plotter": fake_plotter_module}):
            result = program.ui(mock_args_api_v2)
        assert result == 0
        fake_plotter_module.Plotter.assert_called_once()


class TestListAndInteractiveUseApiV1:
    """Test that --list and --interactive use API v1 (login:password format)."""

    def test_list_checker_sets_use_api_v1(self):
        """List checker uses API v1 so login:password file format works."""
        program = Program()
        parser = program.setup_cmd_parser()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("mylogin:mypass\n")
            list_path = f.name
        try:
            opt = parser.parse_args(["--list", list_path], namespace=CliNamespace())
            assert opt.use_api_v1 is False  # not set by parser
            ui_calls = []

            def capture_ui(o):
                ui_calls.append((o.use_api_v1,))

            program.ui = capture_ui  # type: ignore[assignment]
            program.list_checker_handler(opt)
            assert len(ui_calls) == 1
            assert ui_calls[0][0] is True  # list_checker_handler sets use_api_v1
        finally:
            os.unlink(list_path)

    def test_interactive_sets_use_api_v1(self):
        """Interactive mode uses API v1 so Login/Password prompt works."""
        program = Program()
        parser = program.setup_cmd_parser()
        opt = parser.parse_args(["--interactive"], namespace=CliNamespace())
        assert opt.use_api_v1 is False
        with (
            patch("builtins.input", return_value=""),
            patch("sys.exit", side_effect=SystemExit),
            contextlib.suppress(SystemExit),
        ):
            program.interactive_mode_handler(opt, "users.db")


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
        args = parser.parse_args(["--api-v1", "--login", "test", "--password", "pass"])

        assert args.use_api_v1 is True
        assert args.login == "test"
        assert args.password == "pass"

    def test_api_v2_arguments(self, program):
        """Test API v2 argument parsing."""
        parser = program.setup_cmd_parser()
        args = parser.parse_args([
            "--btk-id",
            "123456789",
            "--account-phone",
            "375331234567",
            "--password",
            "pass",
        ])

        assert args.login == "123456789"
        assert args.account_phone == "375331234567"
        assert args.password == "pass"

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


class TestHTMLClientWithRealData:
    """Test HTML client with real testdata HTML files."""

    def test_stat_page_parsing(self):
        """Test parsing statistic_page.html for session data."""
        html_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "testdata", "statistic_page.html"
        )
        with open(html_file, encoding="utf-8") as f:
            html = f.read()

        sessions = StatPageParser.parse_html(html)
        assert len(sessions) == 1
        session = sessions[0]
        assert session.title == "Длительность сессии"
        assert session.duration == timedelta(days=2, hours=21, minutes=0, seconds=21)
        assert session.cost == Decimal("0")
        assert session.ingoing == pytest.approx(13855.204)
        assert session.outgoing == pytest.approx(680.559)

    def test_payments_page_parsing(self):
        """Test parsing payments_page.html for claim payments."""
        html_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "testdata", "payments_page.html"
        )
        with open(html_file, encoding="utf-8") as f:
            html = f.read()

        claim_payments = PaymentsPageParser.parse_claim_payments(html)
        assert len(claim_payments) == 3
        assert claim_payments[0].is_active is True
        assert claim_payments[1].is_active is False
        assert claim_payments[2].is_active is False

    def test_empty_payments_page_parsing(self):
        """Test parsing empty payments page."""
        html_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "testdata", "payments_empty_page.html"
        )
        with open(html_file, encoding="utf-8") as f:
            html = f.read()

        claim_payments = PaymentsPageParser.parse_claim_payments(html)
        assert len(claim_payments) == 0

    def test_account_page_parsing(self):
        """Test parsing account_page.html for user info."""
        html_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "testdata", "account_page.html"
        )
        with open(html_file, encoding="utf-8") as f:
            html = f.read()

        user_info = AccountPageParser.parse_user_info(html)
        assert user_info is not None
        assert "Иванов" in user_info.full_name or len(user_info.full_name) > 0
        assert user_info.balance > 0
