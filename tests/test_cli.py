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
    ByFlyApiClient,
    Program,
    print_traffic_table,
)
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

    @patch("byflypy.cli.TokenManager")
    def test_ui_api_v2(self, mock_token_manager_class, program, mock_args_api_v2):
        """Test UI with API v2."""
        mock_token_manager = Mock()
        mock_token_manager.load.return_value = None
        mock_token_manager_class.return_value = mock_token_manager

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

        original_init = ByFlyApiClient.__init__
        original_login = ByFlyApiClient.login

        def mock_init(
            self, phone=None, password=None, sms_code=None, login=None, token_manager=None
        ):
            self._phone = phone
            self._password = password
            self._sms_code = sms_code
            self._login = login
            self._token_manager = token_manager
            self._session = None
            self._access_token = "test_token"
            self._token_expires_at = None
            self._user = None

        def mock_login(self, use_saved_token=True):
            return True

        def mock_get_contracts(self):
            return [mock_contract]

        def mock_get_traffic_details(self, contract_id, application_id):
            return None

        ByFlyApiClient.__init__ = mock_init  # type: ignore[assignment]
        ByFlyApiClient.login = mock_login  # type: ignore[assignment]
        ByFlyApiClient.get_contracts = mock_get_contracts  # type: ignore[assignment]
        ByFlyApiClient.get_traffic_details = mock_get_traffic_details  # type: ignore[assignment]

        try:
            result = program.ui(mock_args_api_v2)
            assert result == 0
        finally:
            ByFlyApiClient.__init__ = original_init  # type: ignore[assignment]
            ByFlyApiClient.login = original_login
            del ByFlyApiClient.get_contracts
            del ByFlyApiClient.get_traffic_details

    @patch("byflypy.cli.TokenManager")
    def test_ui_api_v2_multiple_logins_error(
        self, mock_token_manager_class, program, mock_args_api_v2
    ):
        """Test UI with API v2 when multiple contracts exist."""
        mock_token_manager = Mock()
        mock_token_manager.load.return_value = None
        mock_token_manager_class.return_value = mock_token_manager

        mock_contract1 = ApiContract(
            id=123,
            user_id=1,
            login="login1",
            btk_id="btk1",
            balance=Decimal("10.00"),
            status="active",
            name="Contract 1",
            addresses=None,
            price=Decimal("0"),
            terminate_in=None,
            applications=[],
            can_add_funds=True,
            can_apply_promised_payment=False,
            max_promised_payment_amount=None,
        )

        mock_contract2 = ApiContract(
            id=456,
            user_id=1,
            login="login2",
            btk_id="btk2",
            balance=Decimal("20.00"),
            status="active",
            name="Contract 2",
            addresses=None,
            price=Decimal("0"),
            terminate_in=None,
            applications=[],
            can_add_funds=True,
            can_apply_promised_payment=False,
            max_promised_payment_amount=None,
        )

        original_init = ByFlyApiClient.__init__
        original_login = ByFlyApiClient.login

        def mock_init(
            self, phone=None, password=None, sms_code=None, login=None, token_manager=None
        ):
            self._phone = phone
            self._password = password
            self._sms_code = sms_code
            self._login = login
            self._token_manager = token_manager
            self._session = None
            self._access_token = "test_token"
            self._token_expires_at = None
            self._user = None

        def mock_login(self, use_saved_token=True):
            return True

        def mock_get_contracts(self):
            return [mock_contract1, mock_contract2]

        ByFlyApiClient.__init__ = mock_init  # type: ignore[assignment]
        ByFlyApiClient.login = mock_login  # type: ignore[assignment]
        ByFlyApiClient.get_contracts = mock_get_contracts  # type: ignore[assignment]

        try:
            result = program.ui(mock_args_api_v2)
            assert result == 2
        finally:
            ByFlyApiClient.__init__ = original_init  # type: ignore[assignment]
            ByFlyApiClient.login = original_login
            del ByFlyApiClient.get_contracts

    @patch("byflypy.cli.TokenManager")
    def test_ui_api_v2_invalid_login(self, mock_token_manager_class, program, mock_args_api_v2):
        """Test UI with API v2 when btk_id is invalid."""
        mock_token_manager = Mock()
        mock_token_manager.load.return_value = None
        mock_token_manager_class.return_value = mock_token_manager

        mock_args_api_v2.login = "invalid_btk_id"

        mock_contract1 = ApiContract(
            id=123,
            user_id=1,
            login="login1",
            btk_id="btk123",
            balance=Decimal("10.00"),
            status="active",
            name="Contract 1",
            addresses=None,
            price=Decimal("0"),
            terminate_in=None,
            applications=[],
            can_add_funds=True,
            can_apply_promised_payment=False,
            max_promised_payment_amount=None,
        )

        original_init = ByFlyApiClient.__init__
        original_login = ByFlyApiClient.login

        def mock_init(
            self, phone=None, password=None, sms_code=None, login=None, token_manager=None
        ):
            self._phone = phone
            self._password = password
            self._sms_code = sms_code
            self._login = None
            self._token_manager = token_manager
            self._session = None
            self._access_token = "test_token"
            self._token_expires_at = None
            self._user = None

        def mock_login(self, use_saved_token=True):
            return True

        def mock_get_contracts(self):
            return [mock_contract1]

        ByFlyApiClient.__init__ = mock_init  # type: ignore[assignment]
        ByFlyApiClient.login = mock_login  # type: ignore[assignment]
        ByFlyApiClient.get_contracts = mock_get_contracts  # type: ignore[assignment]
        try:
            result = program.ui(mock_args_api_v2)
            assert result == 2
        finally:
            ByFlyApiClient.__init__ = original_init  # type: ignore[assignment]
            ByFlyApiClient.login = original_login
            del ByFlyApiClient.get_contracts

    @patch("byflypy.cli.TokenManager")
    @patch("byflypy.cli.HAS_MATPLOT", True)
    def test_ui_api_v2_with_graph_path(self, mock_token_manager_class, program, mock_args_api_v2):
        """Test API v2 path with --graph does not raise NameError (Plotter import)."""
        mock_token_manager = Mock()
        mock_token_manager.load.return_value = None
        mock_token_manager_class.return_value = mock_token_manager

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

        original_init = ByFlyApiClient.__init__
        original_login = ByFlyApiClient.login

        def mock_init(
            self, phone=None, password=None, sms_code=None, login=None, token_manager=None
        ):
            self._phone = phone
            self._password = password
            self._sms_code = sms_code
            self._login = login
            self._token_manager = token_manager
            self._session = None
            self._access_token = "test_token"
            self._token_expires_at = None
            self._user = None

        def mock_login(self, use_saved_token=True):
            return True

        def mock_get_contracts(self):
            return [mock_contract]

        def mock_get_traffic_details(self, contract_id, application_id):
            return TrafficDetails(
                total_incoming=Decimal("100"),
                total_outgoing=Decimal("50"),
                total_traffic=Decimal("150"),
                total_duration="1:00:00",
                sessions=[],
            )

        ByFlyApiClient.__init__ = mock_init  # type: ignore[assignment]
        ByFlyApiClient.login = mock_login  # type: ignore[assignment]
        ByFlyApiClient.get_contracts = mock_get_contracts  # type: ignore[assignment]
        ByFlyApiClient.get_traffic_details = mock_get_traffic_details  # type: ignore[assignment]

        fake_plotter_module = types.ModuleType("byflypy.plotter")
        fake_plotter_module.Plotter = Mock()  # type: ignore[unresolved-attribute]

        try:
            with patch.dict(sys.modules, {"byflypy.plotter": fake_plotter_module}):
                result = program.ui(mock_args_api_v2)
            assert result == 0
            fake_plotter_module.Plotter.assert_called_once()
        finally:
            ByFlyApiClient.__init__ = original_init  # type: ignore[assignment]
            ByFlyApiClient.login = original_login
            del ByFlyApiClient.get_contracts
            del ByFlyApiClient.get_traffic_details


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
            opt = parser.parse_args(["--list", list_path])
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
        opt = parser.parse_args(["--interactive"])
        assert opt.use_api_v1 is False
        with (
            patch("builtins.input", return_value=""),
            patch("sys.exit", side_effect=SystemExit),
            contextlib.suppress(SystemExit),
        ):
            program.interactive_mode_handler(opt, "users.db")
        # Handler sets use_api_v1=True at start before prompting
        assert opt.use_api_v1 is True


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
