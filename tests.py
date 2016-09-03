# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
import codecs
from unittest import TestCase
import unittest
from ByFlyUser import ByFlyUser
import os
from database import Table, DBManager, Record, ErrorDatabase
import database
try:
    import mock
except:
    from unittest import mock

# class TestAccountParse(TestCase):
#     def setUp(self):
#         self.html = codecs.open("2.html", encoding="utf8").read()
#         self.byflyuser = ByFlyUser("test", "test")
#
#     def test_parse_balance(self):
#         self.assertIsInstance(self.byflyuser.parse_account_info(self.html)['balance'], int)
#
#     def test_table_content(self): 
#         print self.byflyuser.get_table_dict(self.html)


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

if __name__ == '__main__':
    unittest.main()