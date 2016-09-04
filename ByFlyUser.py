# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:        byflyuser.py
# Purpose:
#
# Author:      Александр
#
# Created:     28.10.2011
# Copyright:   (c) Александр 2011
# -------------------------------------------------------------------------------
'''User Class'''
from __future__ import unicode_literals, absolute_import
import re
import codecs
from decimal import Decimal
import datetime
import time
import requests
import logging

logger = logging.getLogger(__name__)


class ByflyException(Exception):
    pass


class ByflyEmptyResponseException(ByflyException):
    pass


class ByflyBanException(ByflyException):
    pass


class ByflyAuthException(ByflyException):
    pass


M_BAN = 0
M_SESSION = 1
M_WRONG_PASS = 2
M_REFRESH = 3
M_OK = 4
M_NONE = 5
M_DICT = {
    M_BAN: 'Вы слишком часто пытаетесь войти в систему',
    M_SESSION: 'Время сессии истекло',
    M_WRONG_PASS: 'Неверный логин или пароль',
    M_REFRESH: 'Надо обновить страницу',
    M_OK: 'OK',
    M_NONE: 'Неизвестная ошибка'
}
_DEBUG_ = False


def log_to_file(filename, log_content, force=False):
    """
    log text into file
    :param filename:
    :param log_content:
    :param force: force write if _DEBUG=False
    :return: None
    """
    if _DEBUG_ or force:
        with codecs.open(filename, "w+", encoding="utf8") as f:
            f.write(log_content)


def get_exception_str(e):
    if hasattr(e, 'message'):
        return e.message
    return "{}".format(e)

# Единицы измерения
TRAF_MEASURE = 'Мб'
MONEY_MEASURE = 'руб'

START_PAGE_MARKER = 'Состояние счета'


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


class UserInfo(object):
    def __init__(self, full_name, plan, balance):
        self._full_name = full_name
        self._plan = plan
        self._balance = balance

    @property
    def full_name(self):
        return self._full_name

    @property
    def plan(self):
        return self._plan

    @property
    def balance(self):
        return self._balance


class ByFlyUser(object):
    """Interface to get information
    usage:
        user=ByFlyUser("login","password")
        user.Login() # connect to server and login
        user.PrintInfo() #print account info
    """

    class LoginErrorMessages:
        ERR_BAN = 'Вы совершаете слишком частые попытки авторизации'
        ERR_STUCK_IN_LOGIN = 'Осуществляется вход в систему'
        ERR_TIMEOUT_LOGOUT = 'Сеанс работы после определенного периода бездействия заканчивается'
        ERR_INCORRECT_CRED = 'Введен неверный пароль или абонент не существует'

    _Log1 = '1.html'
    _Log2 = '2.html'
    _Log3 = '3.html'
    _last_error = ''
    _last_exception = None
    URL_LOGIN_PAGE = 'https://issa.beltelecom.by/main.html'
    URL_ACCOUNT_PAGE = 'https://issa.beltelecom.by/main.html'
    URL_STATISTIC_PAGE = 'https://issa.beltelecom.by/statact.html'

    def __init__(self, login, password):
        self._login = login
        self._password = password
        self.info = None
        self.session = requests.session()

    def _set_last_error(self, error, exception=None):
        self._last_error = error
        self._last_exception = exception

    def get_last_error(self):
        if isinstance((self._last_error), int):
            return M_DICT[self._last_error]
        else:
            return "%s" % self._last_error

    def get_last_exception(self):
        return self._last_exception

    def check_error_message(self, html):
        '''Parse html and return 'OK' ,error representation string or None'''
        if not html:
            raise ByflyEmptyResponseException("Server return empty response")
        if html.find(self.LoginErrorMessages.ERR_BAN) != -1:
            raise ByflyBanException(self.LoginErrorMessages.ERR_BAN)
        if html.find(self.LoginErrorMessages.ERR_STUCK_IN_LOGIN) != -1:
            return M_REFRESH
        if html.find(self.LoginErrorMessages.ERR_TIMEOUT_LOGOUT) != -1:
            return M_SESSION
        if html.find(self.LoginErrorMessages.ERR_INCORRECT_CRED) != -1:
            raise ByflyAuthException(self.LoginErrorMessages.ERR_INCORRECT_CRED)
        if html.find(START_PAGE_MARKER) != -1:
            return M_OK
        return M_NONE

    def login(self):
        """
        Function log into byfly profile.
        :return: True if sucess
        """
        if not self._login and not self._password:
            return False
        LANG_ID = 2
        data = {
            'Lang': LANG_ID,
            'oper_user': self._login,
            'passwd': self._password,
        }
        try:
            r = self.session.post(self.URL_LOGIN_PAGE, data=data)
            if r.status_code != 200:
                logger.debug("Login status code is %s", r.status_code)
                return False
            html = r.text
            log_to_file(self._Log1, html)
        except Exception as e:
            logger.exception(e)
            self._set_last_error(get_exception_str(e))
            return False
        try:
            return self.check_error_message(html) == M_OK
        except ByflyException as e:
            logger.exception(e)
            self._set_last_error(get_exception_str(e), e)
            return False
            # k = None
            # if res == M_REFRESH:
            #     k = self.get_info()
            #     if k:
            #         return True
            #     else:
            #         ## Error while get info
            #         return False
            # elif res == M_OK:
            #     return True
            # self._SetLastError(res)
            # return False

    def _get_table_value(self, html, key):
        pass

    def get_account_info_page(self):
        """
        parse a main page of cabinet and return dictionary
        '''
        :return:
        dict keys:
        tarif,FIO,traf,balance,duration
        :rtype: UserInfo,
        """
        try:
            r = self.session.get(self.URL_ACCOUNT_PAGE)
            html = r.text
            log_to_file(self._Log2, html)
        except Exception as e:
            self._set_last_error(get_exception_str(e))
            return False
        return self.parse_account_info(html)
        # m=re.search(
        # u'alt="Тарифный план"></td>.*?<td>&nbsp;<b class=body>(.*?)<', html, 16)
        # if m:
        #     s = m.group(1)
        #     s = s.strip()
        #     k['tarif'] = s
        # else:
        #     self._SetLastError(u'Не определен тариф')
        #     return False
        # m=re.search(u'alt="Пользователь" title="Пользователь"></td>.*?<td>&nbsp;<b class=body>(.*?)</b>',html,16)
        # if m:
        #     s=m.group(1)
        #     s=s.strip()
        #     k['FIO']=s
        # m=re.search(u'длительность сессий</td>.*?<td align=center>&nbsp;(\d*:(\d*))',html,16)
        # if m:
        #     s=m.group(1)
        #     s=s.strip()
        #     comp = s.split(':')
        #     comp = map(int,comp)
        #     if len(comp) == 2:
        #         #min:sec
        #         k['duration'] = datetime.timedelta(minutes=comp[0], seconds=comp[1])
        #     elif len(comp) == 1:
        #         #sec
        #         k['duration'] = datetime.timedelta(seconds=comp[0])
        #     else:
        #         #zero field?
        #         k['duration'] = datetime.timedelta()
        #
        # m=re.search(u'суммарный.трафик</td>.*?<td.align=center>.*?;(\d*(\.(\d*))?)',html,16)
        # if m:
        #     s=m.group(1)
        #     s=s.strip()
        #     try:
        #         k['traf']=float(s)
        #     except:
        #         pass

        # s=str(k.get('traf'))+' '+TRAF_MEASURE if k.get('traf') else k.get('duration')
        # self.info=u"%s - %s\n%s %s - %s"%(k.get("FIO"),k.get('tarif'),k.get('balance'),MONEY_MEASURE,s)
        # return k

    def get_table_dict(self, html):
        k = dict()
        matches = re.findall("<tr[^>]*>[^<]*<td[^>]*>([^<]*)</td>[^<]*<td[^>]*>([^<]*)</td>[^<]*</tr>",
                             html, re.DOTALL)
        for match in matches:
            k[match[0]] = match[1]
        return k

    def parse_account_info(self, html):
        FULL_NAME_KEY = "Абонент"
        PLAN_KEY = "Тарифный план на услуги"
        BALANCE_REGEXPR_PATTERN = 'Актуальный баланс: <b>(.*)</b>'

        def strip_modey_field(s):
            res = ''
            for char in s:
                if char.isdigit() or char in [',', '.']:
                    res += char
            return res

        k = dict()
        m = re.search(BALANCE_REGEXPR_PATTERN, html)
        if m:
            s = m.group(1)
            s = s.strip(" .")
            s = strip_modey_field(s)
            try:
                balance_int = Decimal(s)
            except Exception as e:
                logger.exception(e)
                self._set_last_error('Не определен баланс')
                return False
            balance = balance_int
        else:
            self._set_last_error('Не определен баланс')
            return False
        table_k = self.get_table_dict(html)
        plan = table_k[PLAN_KEY]
        full_name = table_k[FULL_NAME_KEY]
        return UserInfo(full_name, plan, balance)

    def get_log_raw(self, period='current', fromfile=None, encoding='cp1251'):
        """Return report of using connection as raw csv. period='curent' or 'previous. If """
        if not fromfile:
            try:
                param = 'this_month' if period == 'current' else 'last_month'
                r = self.session.get(self.URL_STATISTIC_PAGE + '?{}'.format(param))
                if r.status_code != 200:
                    logger.debug("Statistic page error %s", r.status_code)
                    return False
                raw_html = r.text
                log_to_file(self._Log3, raw_html)
            except Exception as e:
                self._set_last_error(str(e))
                return False
        else:
            try:
                import codecs

                raw_html = codecs.open(fromfile, encoding=encoding).read()
            except Exception as e:
                self._set_last_error(str(e))
                return False
        return raw_html

    #     def SummarySessions(self, sessions):
    #         '''Calculate summary info about sessions and return dictionary representing\
    # (cost,duration,traf)'''
    #         Cost = 0
    #         Duration = datetime.timedelta()
    #         Traf = 0
    #         for session in sessions:
    #             if hasattr(session, 'cost'):
    #                 Cost += session.cost
    #             if hasattr(session, 'ingoing'):
    #                 Traf += session.ingoing
    #             if hasattr(session, 'outgoing'):
    #                 Traf += session.outgoing
    #             if hasattr(session, 'duration'):
    #                 Duration += session.duration
    #
    #         return {'cost': Cost, 'duration': Duration, 'traf': Traf}

    def get_log(self, period='current', fromfile=None,
                encoding='cp1251'):
        """Return report of using connection. period='curent' or 'previous' """
        raw_html = self.get_log_raw(period, fromfile, encoding=encoding)
        if not raw_html:
            return False
        return StatPageParser.parse_html(raw_html)

    def print_to_console(self, s):
        print(s)

    def print_info(self):
        '''Call GetInfo() and print'''
        info = self.get_account_info_page()
        if not info:
            self.print_to_console("Error " + self.get_last_error())
            return False
        # if info.get('traf'):
        #     traf = u"Трафик  - %s %s" % (info.get('traf'),TRAF_MEASURE)
        # else:
        #     traf = ''
        # if info.get('duration'):
        #     duration = u"Длительность  - %s" % (info.get('duration'))
        # else:
        #     duration = ''
        traf = ''
        duration = ''
        self.print_to_console('''\
Абонент - %s
Тариф   - %s
Баланс  - %s %s
%s
%s\
        ''' % (info.full_name, info.plan,
               info.balance, MONEY_MEASURE, traf, duration))
        return True


# def PrintAdditionInfo(self, period=None):
#         '''Print summary information about sessions'''
#         s = (u'-' * 20).center(40) + '\n'
#         summary = self.SummarySessions(self.GetLog(period))
#         format_args = summary
#         format_args.update(globals())
#         s += u'''\
# Суммарный трафик - %(traf)s %(TRAF_MEASURE)s
# Превышение стоимости - %(cost)s %(MONEY_MEASURE)s
# Суммарное время online - %(duration)s''' % (format_args)
#         print (s)


class StatPageParser(object):
    TABLE_RE = '<table[^>]* class="content">.*?</table>'
    ROW_RE = '<tr[^>]*>(.*?)</tr>'
    CELL_RE = '<td[^>]*>(.*?)</td>'
    DATE_FORMAT = '%d.%m.%Y  %H:%M:%S'

    @staticmethod
    def parse_html(html):
        table_html = StatPageParser.get_table(html)
        return [StatPageParser.parse_session(StatPageParser.parse_row(row)) for row in
                StatPageParser.get_rows(table_html)]

    @staticmethod
    def get_table(html):
        tables = re.findall(StatPageParser.TABLE_RE, html, re.DOTALL)
        if not tables:
            return False
        table = tables[1]
        return table

    @staticmethod
    def get_rows(table_html):
        rows = re.findall(StatPageParser.ROW_RE, table_html, re.DOTALL)
        if not rows:
            return False
        rows = rows[1:]
        if not rows:
            return False
        return rows

    @staticmethod
    def parse_row(row_html):
        cells = re.findall(StatPageParser.CELL_RE, row_html, re.DOTALL)
        if not cells:
            return False
        return cells

    @staticmethod
    def parse_session(row_cells):
        assert len(row_cells), 7
        raw_title = row_cells[0]
        raw_begin = row_cells[1]
        raw_end = row_cells[2]
        raw_duration = row_cells[3]
        raw_ingoing = row_cells[4]
        raw_outgoing = row_cells[5]
        raw_cost = row_cells[6]
        try:
            title = raw_title.strip()
            begin = datetime.datetime.strptime(raw_begin, StatPageParser.DATE_FORMAT)
            end = datetime.datetime.strptime(raw_end, StatPageParser.DATE_FORMAT)
            try:
                ttuple = time.strptime(raw_duration, "%d.%H:%M:%S")[2:6]
                duration = datetime.timedelta(days=ttuple[0],
                                              hours=ttuple[1], minutes=ttuple[2],
                                              seconds=ttuple[3])
            except Exception as e:
                time_parts = raw_duration.split(":")
                time_parts = list(reversed(time_parts))
                parts_count = len(time_parts)
                seconds = minutes = hours = 0
                if parts_count > 0:
                    seconds = int(time_parts[0])
                if parts_count > 1:
                    minutes = int(time_parts[1])
                if parts_count > 2:
                    hours = int(time_parts[2])
                duration = datetime.timedelta(hours=hours,
                                              minutes=minutes, seconds=seconds)
                ingoing = float(raw_ingoing)
                outgoing = float(raw_outgoing)
                cost = Decimal(raw_cost)
                return Session(title, begin, end, duration, ingoing, outgoing, cost)
        except Exception as e:
            print(e)
            return None
