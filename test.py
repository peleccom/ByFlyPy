import codecs
from unittest import TestCase
from ByFlyUser import ByFlyUser
import os
from database import Table, DBManager, Record, ErrorDatabase


class TestAccountParse(TestCase):
    def setUp(self):
        self.html = codecs.open("2.html", encoding="utf8").read()
        self.byflyuser = ByFlyUser("test", "test")

    def test_parse_balance(self):
        self.assertIsInstance(self.byflyuser.parse_account_info(self.html)['balance'], int)

    def test_table_content(self):
        print self.byflyuser.get_table_dict(self.html)


class DBTest(TestCase):
    FILENAME = "test.db"

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
