# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
import codecs
import logging
import optparse
from tempfile import NamedTemporaryFile
from unittest import TestCase
import unittest
from datetime import timedelta, datetime
from decimal import Decimal
import requests_mock
import sys
import byflyuser
import os
from database import Table, DBManager, Record, ErrorDatabase
import database
import byfly

try:
    import mock
except:
    from unittest import mock


class DBTest(TestCase):
    FILENAME = ":memory:"

    def setUp(self):
        try:
            os.remove(self.FILENAME)
        except Exception as e:
            pass
        self._table = Table(self.FILENAME)
        self.db_manage = DBManager(self._table)

    def tearDown(self):
        self._table = None
        self.db_manage = None

    def test_add(self):
        self.assertEqual(len(self._table.list()), 0)
        record = Record("a", "b", "c")
        self._table.add(record)
        self.assertEqual(len(self._table.list()), 1)

    def test_delete(self):
        record = Record("a", "b", "c")
        self._table.add(record)
        record = self._table.get("a")
        with self.assertRaises(ErrorDatabase):
            self._table.delete("test")
        self._table.delete(record.pk)
        self.assertEqual(len(self._table.list()), 0)

    def test_get_non_exists(self):
        record = self._table.get(5)
        self.assertIsNone(record)
        record = self._table.get("test")
        self.assertIsNone(record)

    def test_get_password(self):
        record = Record("a", "b", "c")
        self._table.add(record)
        result = self.db_manage.get_password("a")
        self.assertIsNotNone(result)
        result2 = self.db_manage.get_password("c")
        self.assertIsNotNone(result2)
        result3 = self.db_manage.get_password("d")
        self.assertIsNone(result3)
        self.assertEqual(result[0], result2[0])
        self.assertEqual(result[1], result2[1])

    def test_wrong_db_file(self):
        with mock.patch.object(database.db, 'connect', side_effect=IOError("1")):
            with self.assertRaises(ErrorDatabase):
                table = Table(self.FILENAME)

    def test_cant_create_table(self):
        table = Table(self.FILENAME)
        with mock.patch.object(table, '_connection') as mock_connection:
            mock_connection.execute = mock.Mock(side_effect=ValueError("1"))
            with self.assertRaises(ErrorDatabase):
                table.create_table_if_not_exists()

    def test_cant_add_record(self):
        record = Record("a", "b", "c")
        with mock.patch.object(self._table, '_connection') as mock_connection:
            mock_connection.execute = mock.Mock(side_effect=ValueError("1"))
            with self.assertRaises(ErrorDatabase):
                self._table.add(record)

    def test_cant_get(self):
        count_before = len(self._table.list())
        record = Record("test_cant_get", "test_cant_get", "test_cant_get")
        self._table.add(record)
        record = self._table.get("test_cant_get")
        self.assertIsNotNone(record)
        pk = record.pk
        with mock.patch.object(self._table, '_connection') as mock_connection:
            mock_connection.cursor = mock.Mock(side_effect=ValueError("1"))
            record = self._table.get("test_cant_get")
            self.assertIsNone(record)
        self._table.delete(pk)
        self.assertEqual(len(self._table.list()), count_before)

    def test_ui(self):
        with mock.patch.object(sys, 'argv', ["database.py"]):
            with self.assertRaises(SystemExit):
                database.main()
        with mock.patch.object(sys, 'argv', ['database.py', 'test.db']):
            with mock.patch.object(database.Table, '__init__', side_effect=database.ErrorDatabase()):
                with self.assertRaises(SystemExit):
                    database.main()


class TestLogToFile(TestCase):
    def test_log_to_file(self):
        CONTENT = "test"
        f = NamedTemporaryFile(delete=False)
        filename = f.name
        f.close()
        byflyuser.log_to_file(filename, CONTENT)
        self.assertEqual(os.path.getsize(filename), 0)
        byflyuser.log_to_file(filename, CONTENT, True)
        self.assertEqual(os.path.getsize(filename), len(CONTENT))

    def test_log_if_debug(self):
        CONTENT = "test"
        f = NamedTemporaryFile(delete=False)
        filename = f.name
        f.close()
        byflyuser._DEBUG_ = True
        byflyuser.log_to_file(filename, CONTENT)
        self.assertEqual(os.path.getsize(filename), len(CONTENT))
        byflyuser._DEBUG_ = False


class TestSessionClass(TestCase):
    TITLE = "title"
    BEGIN = "Jan 1"
    END = "Feb 1"
    DURATION = timedelta(hours=10)
    INGOING = 10
    OUTGOING = 5
    COST = 15.5

    def test_session(self):
        session = byflyuser.Session(self.TITLE, self.BEGIN, self.END, self.DURATION,
                                    self.INGOING, self.OUTGOING, self.COST)
        str_repr = str(session)
        self.assertEqual(str_repr, "Session<%s  %s>" % (self.BEGIN, self.END))
        self.assertEqual(session.title, self.TITLE)
        self.assertEqual(session.begin, self.BEGIN)
        self.assertEqual(session.end, self.END)
        self.assertEqual(session.duration, self.DURATION)
        self.assertEqual(session.ingoing, self.INGOING)
        self.assertEqual(session.outgoing, self.OUTGOING)
        self.assertEqual(session.cost, self.COST)


class TestUserInfoClass(TestCase):
    FULL_NAME = "Иванов Иван Иванович"
    PLAN = "Домосед"
    BALANCE = Decimal(15.5)

    def test_user_info(self):
        user_info = byflyuser.UserInfo(self.FULL_NAME, self.PLAN, self.BALANCE)
        self.assertEqual(user_info.full_name, self.FULL_NAME)
        self.assertEqual(user_info.balance, self.BALANCE)
        self.assertEqual(user_info.plan, self.PLAN)

class TestTotalStatInfoClass(TestCase):
    def test_total_stat_info(self):
        TRAF = 1000
        COST = 10.5
        total_stat_info = byflyuser.TotalStatInfo(TRAF, COST)
        self.assertEqual(total_stat_info.total_cost, COST)
        self.assertEqual(total_stat_info.total_traf, TRAF)

class TestClaimPaymentClass(TestCase):
    def test_claim_payment(self):
        PK = 1
        DATE = "Jan 1"
        IS_ACTIVE = True
        COST = 10.6
        TYPE_OF_PAYMENTS = 'Обещанный платеж'
        claim_payment = byflyuser.ClaimPayment(PK, DATE, IS_ACTIVE, COST, TYPE_OF_PAYMENTS)
        self.assertEqual(claim_payment.cost, COST)
        self.assertEqual(claim_payment.date, DATE)
        self.assertEqual(claim_payment.is_active, IS_ACTIVE)


class TestByFlyUserClass(TestCase):
    LOGIN = "test"
    PASSWORD = "test"

    def setUp(self):
        self._byflyuser = byflyuser.ByFlyUser(self.LOGIN, self.PASSWORD)

    def test_empty_login(self):
        byflyUser = byflyuser.ByFlyUser("", "")
        with self.assertRaises(byflyuser.ByflyAuthException):
            byflyUser.login()

    def test_login(self):
        with requests_mock.Mocker() as m:
            m.post(self._byflyuser.URL_LOGIN_PAGE, status_code=404)
            with self.assertRaises(byflyuser.ByflyInvalidResponseException):
                self._byflyuser.login()

            # Empty response
            m.post(self._byflyuser.URL_LOGIN_PAGE)
            with self.assertRaises(byflyuser.ByflyEmptyResponseException):
                self._byflyuser.login()
            self.assertIsNotNone(self._byflyuser.get_last_error())
            m.post(self._byflyuser.URL_LOGIN_PAGE, text=byflyuser.START_PAGE_MARKER)
            self.assertTrue(self._byflyuser.login())
            # BAN
            m.post(self._byflyuser.URL_LOGIN_PAGE, text=self._byflyuser.LoginErrorMessages.ERR_BAN)
            with self.assertRaises(byflyuser.ByflyBanException):
                self._byflyuser.login()
            # Wrong cred
            m.post(self._byflyuser.URL_LOGIN_PAGE, text=self._byflyuser.LoginErrorMessages.ERR_INCORRECT_CRED)
            with self.assertRaises(byflyuser.ByflyAuthException):
                self._byflyuser.login()
            # no known marker found

            m.post(self._byflyuser.URL_LOGIN_PAGE, text="test")
            self.assertFalse(self._byflyuser.login())

            m.post(self._byflyuser.URL_LOGIN_PAGE, text=self._byflyuser.LoginErrorMessages.ERR_STUCK_IN_LOGIN)
            self._byflyuser.login()

            m.post(self._byflyuser.URL_LOGIN_PAGE, text=self._byflyuser.LoginErrorMessages.ERR_TIMEOUT_LOGOUT)
            self.assertFalse(self._byflyuser.login())

        with mock.patch.object(self._byflyuser.session, 'post', side_effect=ValueError("1")):
            with self.assertRaises(byflyuser.ByflyInvalidResponseException):
                self._byflyuser.login()

    def test_number_parser(self):
        self.assertEqual(byflyuser.PageParser.strip_number_field("1.25 руб"), 1.25)
        self.assertEqual(byflyuser.PageParser.strip_number_field("1,25 руб"), 1.25)
        self.assertEqual(byflyuser.PageParser.strip_number_field("-1,25 руб"), -1.25)

    def test_acc_info(self):
        with requests_mock.Mocker() as m:
            m.post(self._byflyuser.URL_LOGIN_PAGE, text=byflyuser.START_PAGE_MARKER)
            self._byflyuser.login()
            f = codecs.open("testdata/account_page.html", 'r', encoding='utf8')
            account_raw_data = f.read()
            f.close()
            m.get(self._byflyuser.URL_ACCOUNT_PAGE, text=account_raw_data)
            ui = byfly.UI(self._byflyuser)
            with mock.patch.object(self._byflyuser.session, 'get', side_effect=ValueError("1")):
                self.assertFalse(self._byflyuser.get_account_info_page())
                self.assertFalse(ui.print_info())

            self.assertTrue(self._byflyuser.get_account_info_page())
            self.assertTrue(ui.print_info())

    def test_get_claim_payment(self):
        with requests_mock.Mocker() as m:
            m.post(self._byflyuser.URL_PAYMENTS_PAGE, status_code=404)
            with self.assertRaises(byflyuser.ByflyInvalidResponseException):
                self._byflyuser.get_payments_page()

    def test_send_request(self):
        with self.assertRaises(byflyuser.ByflyException):
            self._byflyuser.send_request("nosuchmethod", "http://example.com")

    def test_get_log(self):
        sessions = self._byflyuser.get_log(fromfile="testdata/statistic_page.html")
        self.assertEqual(len(sessions), 1)
        session = sessions[0]
        self.assertIsInstance(session, byflyuser.Session)
        self.assertEqual(session.duration, timedelta(hours=69, minutes=0, seconds=21))
        self.assertEqual(session.cost, Decimal(0))
        sessions = self._byflyuser.get_log(fromfile="testdata/statistic_page_not_found.html")
        self.assertEqual(len(sessions), 0)

class TestMainProg(TestCase):
    def test_import_plot(self):
        byfly.import_plot()

    DB_FILENAME = "test.db"

    def test_check_image_filename(self):
        class MockValues(object):
            graph = False

        class MockParser(object):
            values = MockValues()

        parser = MockParser()
        with self.assertRaises(optparse.OptionValueError):
            byfly.check_image_filename(None, None, "", parser)
        with self.assertRaises(optparse.OptionValueError):
            byfly.check_image_filename(None, None, "1.png", parser)
        parser.values.graph = True
        byfly.check_image_filename(None, None, "1.png", parser)
        with self.assertRaises(optparse.OptionValueError):
            byfly.check_image_filename(None, None, "1.txt", parser)

    def test_pass_from_db(self):
        LOGIN = "pass_from_db"
        PASSWORD = "123"

        class MockOpt(object):
            login = ""

        opt = MockOpt()
        password = byfly.pass_from_db(LOGIN, self.DB_FILENAME, opt)
        self.assertIsNone(password)
        table = database.Table(self.DB_FILENAME)
        record = table.add(Record(LOGIN, PASSWORD))
        password = byfly.pass_from_db(LOGIN, self.DB_FILENAME, opt)
        self.assertEqual(password, PASSWORD)

        password = byfly.pass_from_db(LOGIN, self.DB_FILENAME, None)
        self.assertIsNone(password)

    def test_setup_cmd_parser(self):
        byfly.Program().setup_cmd_parser()

    def test_ui(self):
        class OptMock(object):
            graph = False
            login = "test"
            password = "test"
            quiet = False
        with requests_mock.Mocker() as m:
            f = codecs.open("testdata/account_page.html", 'r', encoding='utf8')
            account_raw_data = f.read()
            f.close()
            f = codecs.open("testdata/payments_page.html", 'r', encoding='utf8')
            payments_raw_data = f.read()
            f.close()

            m.get(byflyuser.ByFlyUser.URL_ACCOUNT_PAGE, text=account_raw_data)
            m.post(byflyuser.ByFlyUser.URL_LOGIN_PAGE, text=byflyuser.START_PAGE_MARKER)
            m.get(byflyuser.ByFlyUser.URL_PAYMENTS_PAGE, text=payments_raw_data)
            byfly.Program().ui(OptMock())

    @classmethod
    def tearDownClass(cls):
        try:
            os.remove(cls.DB_FILENAME)
        except:
            pass


class TestServerConnection(TestCase):
    def test_wrong_password(self):
        byfly_user = byflyuser.ByFlyUser("demo", "demo")
        with self.assertRaises(byflyuser.ByflyAuthException):
            byfly_user.login()



class TestStatPageParser(TestCase):
    def testparser(self):
        with codecs.open("testdata/statistic_page.html", encoding='utf8') as f:
            html = f.read()
            sessions = byflyuser.StatPageParser.parse_html(html)
            self.assertEqual(len(sessions), 1)
            session = sessions[0]
            self.assertIsInstance(session, byflyuser.Session)
            self.assertEqual(session.duration, timedelta(hours=69, minutes=0, seconds=21))
            self.assertEqual(session.cost, Decimal(0))
            self.assertEqual(session.ingoing, 13855.204)
            self.assertEqual(session.outgoing, 680.559)
            self.assertEqual(session.begin, datetime(year=2016, month=9, day=1, hour=13, minute=12, second=19))

    def testadditionaldata(self):
        with codecs.open("testdata/statistic_page.html", encoding='utf8') as f:
            html = f.read()
            byflyUser = byflyuser.ByFlyUser("demo", "demo")
            with requests_mock.Mocker() as m:
                m.get(byflyuser.ByFlyUser.URL_STATISTIC_PAGE, text=html)
                ui = byfly.UI(byflyUser)
                ui.print_additional_info()

class TestPaymentsPageParser(TestCase):
    def test_parser(self):
        with codecs.open("testdata/payments_page.html", encoding='utf8') as f:
            html = f.read()
            claim_payments = byflyuser.PaymentsPageParser.parse_claim_payments(html)
            self.assertEqual(len(claim_payments), 3)
            self.assertTrue(claim_payments[0].is_active)
            self.assertFalse(claim_payments[1].is_active)

if __name__ == '__main__':
    logging.basicConfig(level=logging.CRITICAL)
    unittest.main()
