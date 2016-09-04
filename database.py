#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# -------------------------------------------------------------------------------
# Name:        database
# Purpose:
#
# Author:      Alexander
#
# Created:     05.02.2012
# Copyright:   (c) Alexander 2012
# Licence:     <your licence>
# -------------------------------------------------------------------------------
import sys
import sqlite3 as db
import logging
import getpass

logger = logging.getLogger(__name__)


class ErrorDatabase(Exception):
    pass


class Record(object):
    def __init__(self, login, password, alias=None, pk=None):
        self._login = login
        self._password = password
        self._alias = alias
        self.set_pk(pk)

    @classmethod
    def from_cursor_row(cls, row):
        return cls(row['login'], row['pass'], row['alias'], pk=row['id'])

    @property
    def login(self):
        return self._login

    @property
    def password(self):
        return self._password

    @property
    def alias(self):
        return self._alias

    @property
    def pk(self):
        return self._pk

    def set_pk(self, pk):
        self._pk = pk


class Table(object):
    DEFAULT_DB_FILENAME = 'users.db'
    SQL_CREATE_TABLE_QUERY = '''CREATE TABLE IF NOT EXISTS USERS (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                login CHAR(25),
                                pass CHAR(25),
                                alias CHAR(25))'''
    SQL_INSERT_QUERY = '''INSERT INTO USERS (login,pass,alias) VALUES (?,?,?)'''
    SQL_LIST_QUERY = '''SELECT * FROM USERS'''
    SQL_DELETE_QUERY = '''DELETE FROM USERS WHERE id=?'''
    SQL_GET_QUERY = '''SELECT * FROM USERS WHERE login=? OR alias=?'''

    def __init__(self, filename=DEFAULT_DB_FILENAME):
        try:
            self._connection = db.connect(filename)
            self.create_table_if_not_exists()
            self._connection.row_factory = db.Row
        except Exception as e:
            logging.exception(e)
            raise ErrorDatabase("Can't open file %s" % filename)

    def close(self):
        self._connection.close()

    def __del__(self):
        self.close()

    def create_table_if_not_exists(self):
        """
        Create new table
        """
        try:
            self._connection.execute(self.SQL_CREATE_TABLE_QUERY)
            self._connection.commit()
        except Exception as e:
            raise ErrorDatabase("Can't create new table")

    def add(self, record):
        """
        Add new entry into database
        :type record: Record
        :param record:
        :return:
        """
        try:
            cursor = self._connection.execute(self.SQL_INSERT_QUERY, [record.login, record.password, record.alias])
            self._connection.commit()
            record.set_pk(cursor.lastrowid)
            return record
        except Exception as e:
            raise ErrorDatabase("Can't add record")

    def get(self, query):
        """
        Get password from entry with login or alias equals to s.
        Return tuple (login,  password) or None
        """
        try:
            cursor = self._connection.cursor()
            cursor.execute(self.SQL_GET_QUERY,
                           [query, query])
            row = cursor.fetchone()
            if row is not None:
                return Record.from_cursor_row(row)
        except Exception as e:
            logger.exception(e)
            pass
        return None

    def delete(self, pk):
        """
        Delete entry with pk
        """
        try:
            pk = int(pk)
            self._connection.execute(self.SQL_DELETE_QUERY, [pk])
        except Exception as e:
            logger.exception(e)
            raise ErrorDatabase("Can't delete entry")

    def list(self):
        results = []
        cursor = self._connection.cursor()
        cursor.execute(self.SQL_LIST_QUERY)
        for row in cursor.fetchall():
            results.append(Record.from_cursor_row(row))
        return results


class DBManager(object):
    """
        Interface to access to database with login and passwords
    """

    def __init__(self, table):
        self._table = table

    def get_password(self, query):
        """
        Get password from entry with login or alias equals to s.
        Return None or tuple of logic and password
        """
        record = self._table.get(query)
        if record:
            return record.login, record.password
        return None


def handle_interactive_mode(table):  # pragma: no cover
    while True:
        print(u'''Manage database:
list     - list of entries
add      - add new entry
del <id> - delete entry by id
q        - quit
''')
        a = raw_input(">>")
        if a == 'list':
            print("%5s|%15s|%15s|%15s|\n" % ('id', 'login', 'password', 'alias'))
            for record in table.list():
                print("%5s|%15s|%15s|%15s|" % (record.pk, record.login, '*', record.alias))
        if a == 'q':
            return
        if a == 'add':
            try:
                login = str(raw_input('login:'))
                if not login:
                    continue
                password = str(getpass.getpass('password:'))
                if not password:
                    continue
                alias = str(raw_input('alias:'))
                record = Record(login, password, alias)
                table.add(record)
            except Exception as e:
                logger.exception(e)
                pass
        if a.startswith('del '):
            l, _, p = a.partition(" ")
            table.delete(p)


def main():
    if len(sys.argv) == 1:
        print('database.py <database_filename>')
        sys.exit(1)
    else:
        table = None
        try:
            table = Table(sys.argv[1])
        except ErrorDatabase as e:
            print(e)
            exit(1)
        handle_interactive_mode(table)


if __name__ == '__main__':
    main()
