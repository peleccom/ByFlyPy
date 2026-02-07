"""Tests for ByFlyPy package."""

import logging
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from tempfile import NamedTemporaryFile
from unittest import mock

import pytest
import requests_mock

import byfly
import byflyuser
import database
from database import DBManager, ErrorDatabase, Record, Table


@pytest.fixture
def db_table():
    """Create a test database table."""
    filename = ":memory:"
    table = Table(filename)
    yield table
    table = None


@pytest.fixture
def db_manager(db_table):
    """Create a test database manager."""
    return DBManager(db_table)


class TestDatabase:
    """Database tests."""

    def test_add(self, db_table):
        """Test adding records."""
        assert len(db_table.list()) == 0
        record = Record("a", "b", "c")
        db_table.add(record)
        assert len(db_table.list()) == 1

    def test_delete(self, db_table):
        """Test deleting records."""
        record = Record("a", "b", "c")
        db_table.add(record)
        record = db_table.get("a")
        with pytest.raises(ErrorDatabase):
            db_table.delete("test")
        db_table.delete(record.pk)
        assert len(db_table.list()) == 0

    def test_get_non_exists(self, db_table):
        """Test getting non-existent records."""
        assert db_table.get(5) is None
        assert db_table.get("test") is None

    def test_get_password(self, db_manager, db_table):
        """Test getting password by login."""
        record = Record("a", "b", "c")
        db_table.add(record)
        result = db_manager.get_password("a")
        assert result is not None
        result2 = db_manager.get_password("c")
        assert result2 is not None
        result3 = db_manager.get_password("d")
        assert result3 is None
        assert result[0] == result2[0]
        assert result[1] == result2[1]

    def test_wrong_db_file(self):
        """Test handling of wrong database file."""
        import sqlite3

        with mock.patch.object(sqlite3, "connect", side_effect=OSError("1")):
            with pytest.raises(ErrorDatabase):
                Table(":memory:")

    def test_cant_create_table(self):
        """Test handling of table creation failure."""
        table = Table(":memory:")
        with mock.patch.object(table, "_connection") as mock_connection:
            mock_connection.execute = mock.Mock(side_effect=ValueError("1"))
            with pytest.raises(ErrorDatabase):
                table.create_table_if_not_exists()

    def test_cant_add_record(self, db_table):
        """Test handling of add record failure."""
        record = Record("a", "b", "c")
        with mock.patch.object(db_table, "_connection") as mock_connection:
            mock_connection.execute = mock.Mock(side_effect=ValueError("1"))
            with pytest.raises(ErrorDatabase):
                db_table.add(record)

    def test_cant_get(self, db_table):
        """Test handling of get failure."""
        count_before = len(db_table.list())
        record = Record("test_cant_get", "test_cant_get", "test_cant_get")
        db_table.add(record)
        record = db_table.get("test_cant_get")
        assert record is not None
        pk = record.pk
        with mock.patch.object(db_table, "_connection") as mock_connection:
            mock_connection.cursor = mock.Mock(side_effect=ValueError("1"))
            assert db_table.get("test_cant_get") is None
        db_table.delete(pk)
        assert len(db_table.list()) == count_before

    def test_ui(self):
        """Test UI error handling."""
        with mock.patch.object(sys, "argv", ["database.py"]):
            with pytest.raises(SystemExit):
                database.main()
        with mock.patch.object(sys, "argv", ["database.py", "test.db"]):
            with mock.patch.object(Table, "__init__", side_effect=database.ErrorDatabase()):
                with pytest.raises(SystemExit):
                    database.main()


@pytest.fixture
def temp_file():
    """Create a temporary file."""
    with NamedTemporaryFile(delete=False) as f:
        filename = f.name
    yield filename
    try:
        os.unlink(filename)
    except Exception:
        pass


class TestLogToFile:
    """Test log_to_file function."""

    def test_log_to_file(self, temp_file):
        """Test basic log_to_file behavior."""
        CONTENT = "test"
        byflyuser.log_to_file(temp_file, CONTENT)
        assert os.path.getsize(temp_file) == 0
        byflyuser.log_to_file(temp_file, CONTENT, True)
        assert os.path.getsize(temp_file) == len(CONTENT)

    def test_log_if_debug(self, temp_file):
        """Test logging when debug mode is enabled."""
        CONTENT = "test"
        byflyuser._DEBUG_ = True
        byflyuser.log_to_file(temp_file, CONTENT)
        assert os.path.getsize(temp_file) == len(CONTENT)
        byflyuser._DEBUG_ = False


class TestSessionClass:
    """Test Session dataclass."""

    TITLE = "title"
    BEGIN = "Jan 1"
    END = "Feb 1"
    DURATION = timedelta(hours=10)
    INGOING = 10
    OUTGOING = 5
    COST = Decimal("15.5")

    def test_session(self):
        """Test Session creation and attributes."""
        session = byflyuser.Session(
            self.TITLE,
            self.BEGIN,
            self.END,
            self.DURATION,
            self.INGOING,
            self.OUTGOING,
            self.COST,
        )
        str_repr = str(session)
        assert str_repr == f"Session<{self.BEGIN}  {self.END}>"
        assert session.title == self.TITLE
        assert session.begin == self.BEGIN
        assert session.end == self.END
        assert session.duration == self.DURATION
        assert session.ingoing == self.INGOING
        assert session.outgoing == self.OUTGOING
        assert session.cost == self.COST


class TestUserInfoClass:
    """Test UserInfo dataclass."""

    FULL_NAME = "Иванов Иван Иванович"
    PLAN = "Домосед"
    BALANCE = Decimal("15.5")

    def test_user_info(self):
        """Test UserInfo creation and attributes."""
        user_info = byflyuser.UserInfo(self.FULL_NAME, self.PLAN, self.BALANCE)
        assert user_info.full_name == self.FULL_NAME
        assert user_info.balance == self.BALANCE
        assert user_info.plan == self.PLAN


class TestTotalStatInfoClass:
    """Test TotalStatInfo dataclass."""

    def test_total_stat_info(self):
        """Test TotalStatInfo creation and attributes."""
        TRAF = Decimal("1000")
        COST = Decimal("10.5")
        total_stat_info = byflyuser.TotalStatInfo(TRAF, COST)
        assert total_stat_info.total_cost == COST
        assert total_stat_info.total_traf == TRAF


class TestClaimPaymentClass:
    """Test ClaimPayment dataclass."""

    def test_claim_payment(self):
        """Test ClaimPayment creation and attributes."""
        PK = 1
        DATE = "Jan 1"
        IS_ACTIVE = True
        COST = Decimal("10.6")
        TYPE_OF_PAYMENTS = "Обещанный платеж"
        claim_payment = byflyuser.ClaimPayment(PK, DATE, IS_ACTIVE, COST, TYPE_OF_PAYMENTS)
        assert claim_payment.cost == COST
        assert claim_payment.date == DATE
        assert claim_payment.is_active == IS_ACTIVE


@pytest.fixture
def byfly_user():
    """Create a test ByFly user."""
    return byflyuser.ByFlyUser("test", "test")


class TestByFlyUserClass:
    """Test ByFlyUser class."""

    def test_empty_login(self):
        """Test login with empty credentials."""
        byflyUser = byflyuser.ByFlyUser("", "")
        with pytest.raises(byflyuser.ByflyAuthException):
            byflyUser.login()

    def test_login(self, byfly_user):
        """Test various login scenarios."""
        with requests_mock.Mocker() as m:
            m.post(byfly_user.URL_LOGIN_PAGE, status_code=404)
            with pytest.raises(byflyuser.ByflyInvalidResponseException):
                byfly_user.login()

            m.post(byfly_user.URL_LOGIN_PAGE)
            with pytest.raises(byflyuser.ByflyEmptyResponseException):
                byfly_user.login()
            assert byfly_user.get_last_error() is not None

            m.post(byfly_user.URL_LOGIN_PAGE, text=byflyuser.START_PAGE_MARKER)
            assert byfly_user.login() is True

            m.post(byfly_user.URL_LOGIN_PAGE, text=byfly_user.LoginErrorMessages.ERR_BAN)
            with pytest.raises(byflyuser.ByflyBanException):
                byfly_user.login()

            m.post(
                byfly_user.URL_LOGIN_PAGE,
                text=byfly_user.LoginErrorMessages.ERR_INCORRECT_CRED,
            )
            with pytest.raises(byflyuser.ByflyAuthException):
                byfly_user.login()

            m.post(byfly_user.URL_LOGIN_PAGE, text="test")
            assert byfly_user.login() is False

            m.post(
                byfly_user.URL_LOGIN_PAGE,
                text=byfly_user.LoginErrorMessages.ERR_STUCK_IN_LOGIN,
            )
            byfly_user.login()

            m.post(
                byfly_user.URL_LOGIN_PAGE,
                text=byfly_user.LoginErrorMessages.ERR_TIMEOUT_LOGOUT,
            )
            assert byfly_user.login() is False

        with mock.patch.object(byfly_user.session, "post", side_effect=ValueError("1")):
            with pytest.raises(byflyuser.ByflyInvalidResponseException):
                byfly_user.login()

    def test_number_parser(self):
        """Test number parsing."""
        assert byflyuser.PageParser.strip_number_field("1.25 руб") == Decimal("1.25")
        assert byflyuser.PageParser.strip_number_field("1,25 руб") == Decimal("1.25")
        assert byflyuser.PageParser.strip_number_field("-1,25 руб") == Decimal("-1.25")

    def test_acc_info(self, byfly_user):
        """Test account info retrieval."""
        with requests_mock.Mocker() as m:
            m.post(byfly_user.URL_LOGIN_PAGE, text=byflyuser.START_PAGE_MARKER)
            byfly_user.login()
            with open("testdata/account_page.html", encoding="utf8") as f:
                account_raw_data = f.read()
            m.get(byfly_user.URL_ACCOUNT_PAGE, text=account_raw_data)
            ui = byfly.UI(byfly_user)
            with mock.patch.object(byfly_user.session, "get", side_effect=ValueError("1")):
                assert byfly_user.get_account_info_page() is None
                assert ui.print_info() is False

            assert byfly_user.get_account_info_page() is not None
            assert ui.print_info() is True

    def test_get_claim_payment(self, byfly_user):
        """Test claim payments retrieval."""
        with requests_mock.Mocker() as m:
            m.post(byfly_user.URL_PAYMENTS_PAGE, status_code=404)
            with pytest.raises(byflyuser.ByflyInvalidResponseException):
                byfly_user.get_payments_page()

    def test_send_request(self, byfly_user):
        """Test send_request error handling."""
        with pytest.raises(byflyuser.ByflyException):
            byfly_user.send_request("nosuchmethod", "http://example.com")

    def test_get_log(self, byfly_user):
        """Test log retrieval from file."""
        sessions = byfly_user.get_log(fromfile="testdata/statistic_page.html")
        assert len(sessions) == 1
        session = sessions[0]
        assert isinstance(session, byflyuser.Session)
        assert session.duration == timedelta(hours=69, minutes=0, seconds=21)
        assert session.cost == Decimal("0")
        sessions = byfly_user.get_log(fromfile="testdata/statistic_page_not_found.html")
        assert len(sessions) == 0


class TestMainProg:
    """Test main program functionality."""

    def test_import_plot(self):
        """Test plot import function."""
        byfly.import_plot()

    def test_pass_from_db(self, tmp_path):
        """Test password retrieval from database."""
        LOGIN = "pass_from_db"
        PASSWORD = "123"
        DB_FILENAME = tmp_path / "test.db"

        class MockOpt:
            login = ""

        opt = MockOpt()
        password = byfly.pass_from_db(LOGIN, str(DB_FILENAME), opt)
        assert password is None
        table = Table(str(DB_FILENAME))
        table.add(Record(LOGIN, PASSWORD))
        password = byfly.pass_from_db(LOGIN, str(DB_FILENAME), opt)
        assert password == PASSWORD

        password = byfly.pass_from_db(LOGIN, str(DB_FILENAME), None)
        assert password is None

    def test_setup_cmd_parser(self):
        """Test command parser setup."""
        byfly.Program().setup_cmd_parser()

    def test_ui(self):
        """Test UI functionality."""

        class OptMock:
            graph = False
            login = "test"
            password = "test"
            quiet = False
            previous_period = False

        with requests_mock.Mocker() as m:
            with open("testdata/account_page.html", encoding="utf8") as f:
                account_raw_data = f.read()
            with open("testdata/payments_page.html", encoding="utf8") as f:
                payments_raw_data = f.read()

            m.get(byflyuser.ByFlyUser.URL_ACCOUNT_PAGE, text=account_raw_data)
            m.post(byflyuser.ByFlyUser.URL_LOGIN_PAGE, text=byflyuser.START_PAGE_MARKER)
            m.get(byflyuser.ByFlyUser.URL_PAYMENTS_PAGE, text=payments_raw_data)
            byfly.Program().ui(OptMock())


class TestServerConnection:
    """Test server connection."""

    def test_wrong_password(self):
        """Test connection with wrong credentials."""
        byfly_user = byflyuser.ByFlyUser("demo", "demo")
        with pytest.raises(byflyuser.ByflyException):
            byfly_user.login()


class TestStatPageParser:
    """Test statistics page parser."""

    def test_parser(self):
        """Test parsing statistics page."""
        with open("testdata/statistic_page.html", encoding="utf8") as f:
            html = f.read()
            sessions = byflyuser.StatPageParser.parse_html(html)
            assert len(sessions) == 1
            session = sessions[0]
            assert isinstance(session, byflyuser.Session)
            assert session.duration == timedelta(hours=69, minutes=0, seconds=21)
            assert session.cost == Decimal("0")
            assert session.ingoing == 13855.204
            assert session.outgoing == 680.559
            assert session.begin == datetime(
                year=2016, month=9, day=1, hour=13, minute=12, second=19
            )

    def test_additional_data(self):
        """Test parsing additional data."""
        with open("testdata/statistic_page.html", encoding="utf8") as f:
            html = f.read()
            byflyUser = byflyuser.ByFlyUser("demo", "demo")
            with requests_mock.Mocker() as m:
                m.get(byflyuser.ByFlyUser.URL_STATISTIC_PAGE, text=html)
                ui = byfly.UI(byflyUser)
                ui.print_additional_info()


class TestPaymentsPageParser:
    """Test payments page parser."""

    def test_parser(self):
        """Test parsing payments page."""
        with open("testdata/payments_page.html", encoding="utf8") as f:
            html = f.read()
            claim_payments = byflyuser.PaymentsPageParser.parse_claim_payments(html)
            assert len(claim_payments) == 3
            assert claim_payments[0].is_active is True
            assert claim_payments[1].is_active is False

    def test_empty_payments_page(self):
        """Test parsing empty payments page."""
        with open("testdata/payments_empty_page.html", encoding="utf8") as f:
            html = f.read()
            claim_payments = byflyuser.PaymentsPageParser.parse_claim_payments(html)
            assert len(claim_payments) == 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.CRITICAL)
    pytest.main([__file__])
