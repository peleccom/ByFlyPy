# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
import codecs
from tempfile import NamedTemporaryFile
from unittest import TestCase
import unittest
from datetime import timedelta
from decimal import Decimal
import ByFlyUser
import os
from database import Table, DBManager, Record, ErrorDatabase
import database
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


class TestLogToFile(TestCase):

    def test_log_to_file(self):
        CONTENT = "test"
        f = NamedTemporaryFile(delete=False)
        filename = f.name
        f.close()
        ByFlyUser.log_to_file(filename, CONTENT)
        self.assertEqual(os.path.getsize(filename), 0)
        ByFlyUser.log_to_file(filename, CONTENT, True)
        self.assertEqual(os.path.getsize(filename), len(CONTENT))

    def test_log_if_debug(self):
        CONTENT = "test"
        f = NamedTemporaryFile(delete=False)
        filename = f.name
        f.close()
        ByFlyUser._DEBUG_ = True
        ByFlyUser.log_to_file(filename, CONTENT)
        self.assertEqual(os.path.getsize(filename), len(CONTENT))
        ByFlyUser._DEBUG_ = False

class TestSessionClass(TestCase):
    TITLE = "title"
    BEGIN = "Jan 1"
    END = "Feb 1"
    DURATION = timedelta(hours=10)
    INGOING = 10
    OUTGOING = 5
    COST = 15.5

    def test_session(self):
        session = ByFlyUser.Session(self.TITLE, self.BEGIN, self.END, self.DURATION,
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
        user_info = ByFlyUser.UserInfo(self.FULL_NAME, self.PLAN, self.BALANCE)
        self.assertEqual(user_info.full_name, self.FULL_NAME)
        self.assertEqual(user_info.balance, self.BALANCE)
        self.assertEqual(user_info.plan, self.PLAN)
if __name__ == '__main__':
    unittest.main()