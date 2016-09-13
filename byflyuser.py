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
from __future__ import unicode_literals, absolute_import, print_function
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

class ByflyInvalidResponseException(ByflyException):
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


class TotalStatInfo(object):
    def __init__(self, total_traf, total_cost):
        self._total_cost = total_cost
        self._total_traf = total_traf

    @property
    def total_cost(self):
        return self._total_cost

    @property
    def total_traf(self):
        return self._total_traf


class ClaimPayment(object):
    def __init__(self, pk, date, is_active, cost, type_of_payment):
        self._is_active = is_active
        self._cost = cost
        self._pk = pk
        self._date = date
        self._type_of_payment = type_of_payment

    @property
    def is_active(self):
        return self._is_active

    @property
    def date(self):
        return self._date

    @property
    def cost(self):
        return self._cost

class ByFlyUser(object):
    """Interface to get information
    usage:
        user=ByFlyUser("login","password")
        user.Login() # connect to server and login
        user.PrintInfo() #print account info
    """

    class LoginErrorMessages(object):
        ERR_BAN = 'Вы совершаете слишком частые попытки авторизации'
        ERR_STUCK_IN_LOGIN = 'Осуществляется вход в систему'
        ERR_TIMEOUT_LOGOUT = 'Сеанс работы после определенного периода бездействия заканчивается'
        ERR_INCORRECT_CRED = 'Введен неверный пароль или абонент не существует'

    _Log1 = '1.html'
    _Log2 = '2.html'
    _Log3 = '3.html'
    _Log4 = '4.html'
    _last_error = ''
    _last_exception = None
    URL_LOGIN_PAGE = 'https://issa.beltelecom.by/main.html'
    URL_ACCOUNT_PAGE = 'https://issa.beltelecom.by/main.html'
    URL_STATISTIC_PAGE = 'https://issa.beltelecom.by/statact.html'
    URL_PAYMENTS_PAGE = 'https://issa.beltelecom.by/payact.html'

    def __init__(self, login, password):
        self._login = login
        self._password = password
        self.info = None
        self.session = requests.session()

    def _set_last_error(self, error, exception=None):
        self._last_error = error
        self._last_exception = exception

    def get_last_error(self):
        return "%s" % self._last_error

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
        """
        if not self._login and not self._password:
            raise ByflyAuthException("Пустой пароль или логин")
        LANG_ID = 2
        data = {
            'Lang': LANG_ID,
            'oper_user': self._login,
            'passwd': self._password,
        }
        html = self.send_request('post', self.URL_LOGIN_PAGE, logfile=self._Log1, data=data)
        try:
            return self.check_error_message(html) == M_OK
        except ByflyException as e:
            logger.exception(get_exception_str(e))
            raise

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
            html = self.send_request('get', self.URL_ACCOUNT_PAGE, logfile=self._Log2)
        except Exception as e:
            self._set_last_error(get_exception_str(e))
            return False
        return AccountPageParser.parse_user_info(html)

    def get_log_raw(self, previous_period=False, fromfile=None, encoding='utf8'):
        """Return report of using connection as raw csv. period='curent' or 'previous. If """
        if not fromfile:
            try:
                param = 'this_month' if not previous_period else 'last_month'
                raw_html = self.send_request('get', self.URL_STATISTIC_PAGE + '?{}'.format(param), logfile=self._Log3)
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

    def get_log(self, previous_period=False, fromfile=None,
                encoding='utf8'):
        """Return report of using connection. period='curent' or 'previous' """
        raw_html = self.get_log_raw(previous_period, fromfile, encoding=encoding)
        if not raw_html:
            return []
        return StatPageParser.parse_html(raw_html)

    def get_additional_info(self):
        raw_html = self.get_log_raw()
        return StatPageParser.parse_total_stat_info(raw_html)

    def get_payments_page(self):
        html = self.send_request("get", self.URL_PAYMENTS_PAGE, logfile=self._Log4)
        return PaymentsPageParser.parse_claim_payments(html)

    def send_request(self, method, url, **kwargs):
        try:
            logfile = kwargs.pop("logfile", None)
            method = getattr(self.session, method)
        except AttributeError:
            raise ByflyException("Invalid method {}".format(method))
        try:
            r = method(url, **kwargs)
            if r.status_code != 200:
                raise ByflyInvalidResponseException("Page status code is {}".format(r.status_code))
            html = r.text
            if logfile:
                log_to_file(logfile, html)
        except Exception as e:
            raise ByflyInvalidResponseException(get_exception_str(e))
        return html

    def get_money_measure(self):
        return MONEY_MEASURE

    def get_traf_measure(self):
        return TRAF_MEASURE

class PageParser(object):
    @classmethod
    def get_table_dict(cls, html):
        STRIP_CHARS = ": \r\n"
        TAGS_RE = re.compile('<[^<]+?>')
        k = dict()
        matches = re.findall("<tr[^>]*>[^<]*<td[^>]*>(.*?)</td[^>]*>[^<]*<td[^>]*>(.*?)</td[^>]*>[^<]*</tr>",
                             html, re.DOTALL)
        for match in matches:
            key = match[0]
            key = re.sub(TAGS_RE, '', key)
            key = key.strip(STRIP_CHARS)
            value = match[1]
            value = re.sub(TAGS_RE, '', value)
            value = value.strip(STRIP_CHARS)
            k[key] = value
        return k

    @classmethod
    def strip_number_field(cls, s):
        res = ''
        for char in s:
            if char.isdigit() or char in ['-', ',', '.']:
                res += char
            else:
                break
        res = res.replace(",", ".")
        return Decimal(res)

    @classmethod
    def get_tables(cls, html):
        TABLE_RE = '<table[^>]*>.*?</table[^>]*>'
        matches = re.findall(TABLE_RE, html, re.DOTALL)
        return [cls.get_row(match) for match in matches]

    @classmethod
    def get_row(cls, table_html):
        ROW_RE = '<tr[^>]*>.*?</tr[^>]*>'
        matches = re.findall(ROW_RE, table_html, re.DOTALL)
        return [cls.get_cell(match) for match in matches]

    @classmethod
    def get_cell(cls, table_html):
        CELL_RE = '<td[^>]*>(.*?)</td[^>]*>'
        matches = re.findall(CELL_RE, table_html, re.DOTALL)
        return [cls.strip_tags(match) for match in matches]

    @classmethod
    def strip_tags(cls, html):
        TAGS_RE = re.compile('<[^<]+?>')
        return re.sub(TAGS_RE, '', html)

class AccountPageParser(PageParser):
    @classmethod
    def parse_user_info(cls, html):
        FULL_NAME_KEY = "Абонент"
        PLAN_KEY = "Тарифный план на услуги"
        balance = cls.parse_balance(html)
        if not balance:
            return
        table_k = cls.get_table_dict(html)
        plan = table_k[PLAN_KEY]
        full_name = table_k[FULL_NAME_KEY]
        return UserInfo(full_name, plan, balance)

    @classmethod
    def parse_balance(cls, html):
        BALANCE_REGEXPR_PATTERN = 'Актуальный баланс: <b>(.*)</b>'
        m = re.search(BALANCE_REGEXPR_PATTERN, html)
        if m:
            s = m.group(1)
            s = s.strip(" .")
            s = cls.strip_number_field(s)
            try:
                return Decimal(s)
            except Exception as e:
                logger.exception(get_exception_str(e))
                logger.debug('Не определен баланс')
                return


class StatPageParser(PageParser):
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

    @classmethod
    def parse_total_stat_info(cls, html):
        KEY_SUM_COST = "Сумма"
        KEY_SUM_TRAF = "Суммарный трафик"
        if not html:
            return None
        try:
            d = cls.get_table_dict(html)
            cost = d[KEY_SUM_COST]
            traf = d[KEY_SUM_TRAF]
            cost = cls.strip_number_field(cost)
            traf = cls.strip_number_field(traf)
            return TotalStatInfo(traf, cost)
        except Exception as e:
            return None

class PaymentsPageParser(PageParser):
    @classmethod
    def parse_claim_payments(cls, html):
        claim_payments = []
        tables = cls.get_tables(html)
        for table in tables:
            if len(table) > 0:
                row = table[0]
                if len(row) > 0:
                    cell = row[0]
                    if cell.startswith('Зачисленные обещанные платежи'):
                        if len(table) > 2:
                            for row in table[2:]:
                                assert len(row), 5
                                is_active = row[3] == "Активен"
                                claim_payments.append(ClaimPayment(row[0], row[1], is_active, row[2], row[4]))
        return claim_payments