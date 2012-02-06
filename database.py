# -*- coding: UTF-8 -*-

#-------------------------------------------------------------------------------
# Name:        database
# Purpose:
#
# Author:      Alexander
#
# Created:     05.02.2012
# Copyright:   (c) Alexander 2012
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

class ErrorDatabase(Exception):
    """
        Exception of class
    """

class DBLogin(object):
    """
        Iterface to access to database with login and passwords
    """
    import sqlite3 as db

    def __init__(self, filename='users.db'):
        try:
            self._c=self.db.connect(filename)
            self._new()
            self._c.row_factory = self.db.Row
        except Exception,e:
            print e
            raise ErrorDatabase("Can't open file %s"%(filename))

    def __del__(self):
        self._c.close()

    def Add(self,login,password, alias = ''):
        """Add new entry to database"""
        self._c.execute('''INSERT INTO USERS (login,pass,alias) VALUES (?,?,?)''',[login,password,alias])
        self._c.commit()

    def _new(self):
        """Create new table"""
        try:
            self._c.execute('''CREATE TABLE IF NOT EXISTS USERS (id INTEGER PRIMARY KEY AUTOINCREMENT,
  login CHAR(25),
  pass CHAR(25),
  alias CHAR(25))''')
            self._c.commit()
        except:
            raise ErrorDatabase('Can\'t create new table')
    def PrintList(self):
        """Print list of entries"""
        cu=self._c.cursor()
        cu.execute('''SELECT * FROM USERS''')
        print("%5s|%15s|%15s|%15s|\n"%('id','login','password','alias'))
        for row in cu.fetchall():
            print("%5s|%15s|%15s|%15s|"%(row['id'],row['login'],'*', row['alias']))

    def GetPassword(self,s):
        """Get password from entry with login or alias equals to s.
        Return None or tuple of loginc and password"""
        password = None
        login = s
        try:
            cu = self._c.cursor()
            cu.execute('''SELECT * FROM USERS WHERE login=? or alias=?''',[s,s])
            row=cu.fetchone()
            if row!=None:
                print (u'Пароль взят из БД')
                password = row['pass']
                try:
                    ## если введенный логин не число то это алиас в базе данных
                    k=int(s)
                except:
                    login=row['login']
        except Exception,e:
            print e.message
        if password:
            return [login,password]
        else:
            return None

    def DeleteEntry(self,id):
        """Delete entry with such id"""
        if not isinstance(id,int):
            print('Incorrect param to DeleteEntry')
            return False
        self._c.execute('''DELETE * FROM USERS WHERE id=?''',id)
        print("Entry deleted")
        return True



def main():
    import sys
    if len(sys.argv) == 1:
        print ('database.py <database_filename>')
    else:
        try:
            o = DBLogin(sys.argv[1])
        except ErrorDatabase,e:
            print e
            exit(1)
        while True:
            print(u'''Manage database:
    list     - list of entries
    add      - add new entry
    del <id> - delete entry by id
    q        - quit
    ''')
            a = raw_input()
            if a == 'list':
                o.PrintList()
            if a == 'q':
                exit()
            if a == 'add':
                try:
                    login = str(raw_input('login:'))
                    if not login:
                        continue
                    password = str(raw_input('password:'))
                    if not password:
                        continue
                    alias = str(raw_input('alias:'))
                    o.Add(login,password,alias)
                except:
                    pass
<<<<<<< HEAD
            if a.startswith('del '):
                l,_,p = a.partition(" ")
                o.DeleteEntry(p)
=======
>>>>>>> origin/master
if __name__ == '__main__':
    main()
