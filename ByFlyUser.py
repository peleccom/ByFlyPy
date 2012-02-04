# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:        ByFlyUser.py
# Purpose:
#
# Author:      Александр
#
# Created:     28.10.2011
# Copyright:   (c) Александр 2011
#-------------------------------------------------------------------------------
'''User Class'''
import cookielib
import urllib
import urllib2
import time
import re
import UnicodeCSV
import datetime
M_BAN = 0
M_SESSION = 1
M_WRONG_PASS = 2
M_REFRESH = 3
M_OK = 4
M_NONE = 5
M_DICT = {
         M_BAN:u'Вы слишком часто пытаетесь войти в систему',
         M_SESSION:u'Время сессии истекло',
         M_WRONG_PASS:u'Неверный логин или пароль',
         M_REFRESH:u'Надо обновить страницу',
         M_OK:u'OK',
         M_NONE:u'Неизвестная ошибка'
         }
_DEBUG_ = False
class Session(object):
    """
        Internet session class
    """

    def __init__(self, title, begin, end, duration, ingoing, outgoing, cost):
        self.title = title
        self.begin = begin
        self.end = end
        self.duration = duration
        self.ingoing = ingoing
        self.outgoing = outgoing
        self.cost = cost
    def __str__(self):
        return "Session<%s  %s>" % (self.begin, self.end)
class ByFlyUser:
    """Interface to get information
    usage:
        user=ByFlyUser("login","password")
        user.Login() # connect to server and login
        user.PrintInfo() #print account info
    """
    _Log1 = '1.html'
    _Log2 = '2.html'
    _LastErr = ''
    _User_Agent = 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.13 (KHTML, like Gecko) Chrome/9.0.597.84 Safari/534.13'
    _Login_Page = 'https://issa.beltelecom.by/cgi-bin/cgi.exe?function=is_login'
    _Account_Page = 'https://issa.beltelecom.by/cgi-bin/cgi.exe?function=is_account'
    def __init__(self, login, password):
        self._login = login
        self._password = password
        self._cj = cookielib.CookieJar()
        self._opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self._cj))
        self._opener.addheaders = [
        ('User-agent', self._User_Agent ),
        ('Accept','text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        ]
        self.info = None

    def _SetLastError(self, error):
        self._LastErr = error

    def LastError(self):
        if isinstance((self._LastErr), int):
            return M_DICT[self._LastErr]
        else:
            return u"%s" % self._LastErr
    def ErrorParser(self, html):
        '''Parse html and return 'OK' ,error representation string or None'''
        err1 = u'Вы слишком часто пытаетесь войти в систему'
        err2 = u'Осуществляется вход в систему'
        err3 = u'Сеанс работы после определенного периода бездействия заканчивается'
        err4 = u'Состояние счета'
        err5 = u'Введен неверный пароль, либо этот номер заблокирован'
        if html.find(err1) != -1:
            return M_BAN
        if html.find(err2) != -1:
            return M_REFRESH
        if html.find(err3) != -1:
            return M_SESSION
        if html.find(err5) != -1:
            return M_WRONG_PASS
        if html.find(err4) != -1:
            return M_OK
        return M_NONE
    def Login(self):
        '''Function log into byfly profile. Return True if sucess'''
        if not self._login and not self._password:
            return False
        data = (('Lang','2'), ('mobnum',self._login), ('Password',self._password))
        enc_data = urllib.urlencode(data)
        try:
            html = self._opener.open(self._Login_Page, enc_data).read().decode('cp1251')
            if _DEBUG_:
                open(self._Log1, 'w+').write(html.encode('cp1251'))
        except urllib2.URLError, error:
            self._SetLastError(error)
            return False
        res = self.ErrorParser(html)
        k = None
        if res == M_REFRESH:
            k = self.GetInfo()
            if k:
                return True
            else:
                ## Error while get info
                return False
        elif res == M_OK:
            return True
        self._SetLastError(res)
        return False

    def GetInfo(self):
        '''
parse a main page of cabinet and return dictionary
keys:
tarif,FIO,traf,balance,duration
        '''
        try:
            html = self._opener.open(self._Account_Page).read().decode('cp1251')
            if _DEBUG_:
                dec = html.encode('cp1251')
                open(self._Log2, 'w+').write(dec)
        except Exception, e:
            self._SetLastError(str(e))
            return False
        k={}
        m=re.search(
        u'alt="Тарифный план"></td>.*?<td>&nbsp;<b class=body>(.*?)<', html, 16)
        if m:
            s = m.group(1)
            s = s.strip()
            k['tarif'] = s
        else:
            self._SetLastError(u'Не определен тариф')
            return False
        m=re.search(u'alt="Пользователь" title="Пользователь"></td>.*?<td>&nbsp;<b class=body>(.*?)</b>',html,16)
        if m:
            s=m.group(1)
            s=s.strip()
            k['FIO']=s
        m=re.search(u'длительность сессий</td>.*?<td align=center>&nbsp;(\d*:(\d*))',html,16)
        if m:
            s=m.group(1)
            s=s.strip()
            k['duration']=s
        m=re.search(u'суммарный.трафик</td>.*?<td.align=center>.*?;(\d*(\.(\d*))?)',html,16)
        if m:
            s=m.group(1)
            s=s.strip()
            try:
                k['traf']=float(s)
            except:
                pass
        m=re.search(u'Актуальный.баланс:</td>.*?<td.class=light.width="50%">.*?;(.?\d*)',html,16)
        if m:
            s=m.group(1)
            s=s.strip()
            k['balance']=s
        else:
            self._SetLastError(u'Не определен баланс')
            return False
        s=str(k.get('traf'))+' MB' if k.get('traf') else k.get('duration')
        self.info="%s - %s\n%s- %s"%(k.get("FIO"),k.get('tarif'),k.get('balance'),s)
        return k

    def GetLogRaw(self,period='current',fromfile=None,encoding='cp1251'):
        """Return report of using connection as raw csv. period='curent' or 'previous. If """
        if not fromfile:
            try:
                req=self._opener.open('https://issa.beltelecom.by/cgi-bin/cgi.exe?function=is_lastcalls&action=report')
                periods='CURRENT'
                if period=='current':
                    periods='CURRENT'
                elif period=='previous':
                    periods='0'
                req=self._opener.open('https://issa.beltelecom.by/cgi-bin/cgi.exe?function=is_lastcalls',urllib.urlencode([('periods',periods),('action','setperiod'),('x','17'),('y','15')]))
                req=self._opener.open('https://issa.beltelecom.by/cgi-bin/cgi.exe?function=is_lastcalls&action=refresh')
                req=self._opener.open('https://issa.beltelecom.by/cgi-bin/cgi.exe?function=is_lastcalls&action=setfilter&filter=0')
                req=self._opener.open('https://issa.beltelecom.by/cgi-bin/cgi.exe?function=is_lastcalls&action=save&repFormat=1&repPostfix=2csv')
                rawcsv=req.read().decode('cp1251')
            except Exception,e:
                self._SetLastError(str(e))
                return false
        else:
            try:
                import codecs
                rawcsv=codecs.open(fromfile,encoding=encoding).read()
            except Exception,e:
                self._SetLastError(str(e))
                return False
        return rawcsv
    def _parsesessions(self,row,title):
        """parsing a row of cvs file"""
        try:
            for i,l in enumerate(title):
                if l == u'Название услуги':
                    title = row[i]
                elif l == u'Дата':
                    begin = datetime.datetime.strptime(row[i], '%d.%m.%Y  %H:%M:%S')
                elif l == u'Окончание сессии':
                    end = datetime.datetime.strptime(row[i], '%d.%m.%Y  %H:%M:%S')
                elif l == u'Длительность':
                    try:
                        duration = time.strptime(row[i], "%d.%H:%M:%S")
                    except Exception, e:
                        duration = time.strptime(row[i], "%H:%M:%S")
                elif l == u'Вх. трафик':
                    m = re.search(u"(\d*\.\d{0,5}).*?(Мб*)", row[i])
                    if len(m.groups())==2:
                        if m.group(2) == u'Мб':
                            ingoing = float(m.group(1))
                elif l == u'Исх. трафик':
                    m = re.search(u"(\d*\.\d{0,5}).*?(Мб*)", row[i])
                    if len(m.groups()) == 2:
                        if m.group(2) == u'Мб':
                            outgoing = float(m.group(1))
                elif l == u'Сумма':
                    m = re.search(u"(\d*)",row[i])
                    cost = float(m.group(1))
            try:
                return Session(title,begin,end,duration,ingoing,outgoing,cost)
            except:
                return None
        except Exception, e:
            self._SetLastError(str(e))
            return None
    def GetLog(self, period='current', fromfile=None,
    encoding='cp1251'):
        """Return report of using connection. period='curent' or 'previous' """
        raw_csv = self.GetLogRaw(period,fromfile,encoding=encoding)
        if not raw_csv:
            return False
        reader = UnicodeCSV.unicode_csv_reader(raw_csv.split('\n'), delimiter = ';')
        title=reader.next()
        it = [k for k in [self._parsesessions(i, title) for i in reader] if k][::-1]
        return it
    def PrintInfo(self):
        '''Call GetInfo() and print'''
        info = self.GetInfo()
        if not info:
            print ("Error "+self.LastError())
            return False
        if info.get('traf'):
            traf = u"Трафик  - %s" % info.get('traf')
        else:
            traf = ''
        if info.get('duration'):
            duration = u"Длительность  - %s" % info.get('duration')
        else:
            duration = ''
        print (u'''\
Абонент - %s
Тариф   - %s
Баланс  - %s
%s
%s\
        '''%(info.get('FIO'), info.get('tarif'),
         info.get('balance'), traf, duration))
        return True
