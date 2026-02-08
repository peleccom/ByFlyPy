"""User module for ByFly API interaction and HTML parsing."""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import requests

from byflypy.models import ClaimPayment, Session, TotalStatInfo, UserInfo

logger = logging.getLogger(__name__)

__all__ = [
    "ByFlyHtmlClient",
    "ByFlyError",
    "ByFlyEmptyResponseError",
    "ByFlyBanError",
    "ByFlyAuthError",
    "ByFlyInvalidResponseError",
    "get_exception_str",
    "log_to_file",
]


class ByFlyError(Exception):
    """Base exception for ByFly-related errors."""


class ByFlyEmptyResponseError(ByFlyError):
    """Raised when server returns an empty response."""


class ByFlyBanError(ByFlyError):
    """Raised when too many login attempts have been made."""


class ByFlyAuthError(ByFlyError):
    """Raised when authentication fails."""


class ByFlyInvalidResponseError(ByFlyError):
    """Raised when server returns an invalid response."""


# Backwards compatibility aliases
ByflyException = ByFlyError
ByflyEmptyResponseException = ByFlyEmptyResponseError
ByflyBanException = ByFlyBanError
ByflyAuthException = ByFlyAuthError
ByflyInvalidResponseException = ByFlyInvalidResponseError


M_BAN = 0
M_SESSION = 1
M_WRONG_PASS = 2
M_REFRESH = 3
M_OK = 4
M_NONE = 5

M_DICT = {
    M_BAN: "Вы слишком часто пытаетесь войти в систему",
    M_SESSION: "Время сессии истекло",
    M_WRONG_PASS: "Неверный логин или пароль",
    M_REFRESH: "Надо обновить страницу",
    M_OK: "OK",
    M_NONE: "Неизвестная ошибка",
}

_DEBUG_ = False

TRAF_MEASURE = "Мб"
MONEY_MEASURE = "руб"

START_PAGE_MARKER = "Состояние счета"


def log_to_file(filename: str, log_content: str, force: bool = False) -> None:
    """Log text to file.

    Args:
        filename: Path to log file
        log_content: Content to log
        force: Force write if _DEBUG is False
    """
    if _DEBUG_ or force:
        with open(filename, "w", encoding="utf8") as f:
            f.write(log_content)


def get_exception_str(e: Exception) -> str:
    """Get string representation of exception."""
    return getattr(e, "message", str(e))


class ByFlyHtmlClient:
    """Interface to get information from ByFly ISP via HTML scraping.

    Usage:
        client = ByFlyHtmlClient("login", "password")
        client.login()
        info = client.get_account_info_page()
        print(info.full_name)
        print(info.balance)
    """

    class LoginErrorMessages:
        """Error messages returned during login."""

        ERR_BAN = "Вы совершаете слишком частые попытки авторизации"
        ERR_STUCK_IN_LOGIN = "Осуществляется вход в систему"
        ERR_TIMEOUT_LOGOUT = "Сеанс работы после определенного периода бездействия заканчивается"
        ERR_INCORRECT_CRED = "Введен неверный пароль или абонент не существует"
        ERR_PLEASE_RETRY = "Произошла ошибка. Попробуйте позже"

    _Log1 = "1.html"
    _Log2 = "2.html"
    _Log3 = "3.html"
    _Log4 = "4.html"

    URL_LOGIN_PAGE = "https://issaold.beltelecom.by/main.html"
    URL_ACCOUNT_PAGE = "https://issaold.beltelecom.by/main.html"
    URL_STATISTIC_PAGE = "https://issaold.beltelecom.by/statact.html"
    URL_PAYMENTS_PAGE = "https://issaold.beltelecom.by/payact.html"

    def __init__(self, login: str, password: str) -> None:
        """Initialize ByFly HTML client.

        Args:
            login: Username
            password: Password
        """
        self._login = login
        self._password = password
        self.info = None
        self.session = requests.session()
        self._last_error = ""
        self._last_exception = None

    def _set_last_error(self, error: str, exception: Optional[Exception] = None) -> None:
        """Set last error information."""
        self._last_error = error
        self._last_exception = exception

    def get_last_error(self) -> str:
        """Get last error message."""
        return str(self._last_error)

    def check_error_message(self, html: str) -> int:
        """Parse HTML and return status code."""
        if not html:
            raise ByFlyEmptyResponseError("Server return empty response")

        if self.LoginErrorMessages.ERR_BAN in html:
            raise ByFlyBanError(self.LoginErrorMessages.ERR_BAN)
        if self.LoginErrorMessages.ERR_STUCK_IN_LOGIN in html:
            return M_REFRESH
        if self.LoginErrorMessages.ERR_TIMEOUT_LOGOUT in html:
            return M_SESSION
        if self.LoginErrorMessages.ERR_PLEASE_RETRY in html:
            raise ByFlyError(self.LoginErrorMessages.ERR_PLEASE_RETRY)
        if self.LoginErrorMessages.ERR_INCORRECT_CRED in html:
            raise ByFlyAuthError(self.LoginErrorMessages.ERR_INCORRECT_CRED)
        if START_PAGE_MARKER in html:
            return M_OK
        return M_NONE

    def login(self) -> bool:
        """Log into ByFly profile."""
        if not self._login and not self._password:
            raise ByFlyAuthError("Пустой пароль или логин")

        LANG_ID = 2
        data = {
            "Lang": LANG_ID,
            "oper_user": self._login,
            "passwd": self._password,
        }
        html = self.send_request("post", self.URL_LOGIN_PAGE, logfile=self._Log1, data=data)
        try:
            return self.check_error_message(html) == M_OK
        except ByFlyError as e:
            logger.exception(get_exception_str(e))
            raise

    def get_account_info_page(self) -> Optional[UserInfo]:
        """Parse main page and return account information."""
        try:
            html = self.send_request("get", self.URL_ACCOUNT_PAGE, logfile=self._Log2)
        except Exception as e:
            self._set_last_error(get_exception_str(e))
            return None
        info = AccountPageParser.parse_user_info(html)
        if info is None:
            self._set_last_error("Failed to parse account info")
            return None
        return info

    def get_log_raw(
        self,
        previous_period: bool = False,
        fromfile: Optional[str] = None,
        encoding: str = "utf8",
    ) -> Optional[str]:
        """Return connection report as raw HTML."""
        if not fromfile:
            try:
                param = "this_month" if not previous_period else "last_month"
                raw_html = self.send_request(
                    "get", f"{self.URL_STATISTIC_PAGE}?{param}", logfile=self._Log3
                )
            except Exception as e:
                self._set_last_error(str(e))
                return None
        else:
            try:
                with open(fromfile, encoding=encoding) as f:
                    raw_html = f.read()
            except Exception as e:
                self._set_last_error(str(e))
                return None
        return raw_html

    def get_log(
        self,
        previous_period: bool = False,
        fromfile: Optional[str] = None,
        encoding: str = "utf8",
    ) -> list[Session]:
        """Return parsed connection report."""
        raw_html = self.get_log_raw(previous_period, fromfile, encoding=encoding)
        if not raw_html:
            return []
        return StatPageParser.parse_html(raw_html)

    def get_additional_info(self) -> Optional[TotalStatInfo]:
        """Get total statistics information."""
        raw_html = self.get_log_raw()
        return StatPageParser.parse_total_stat_info(raw_html)

    def get_payments_page(self) -> list[ClaimPayment]:
        """Get claim payments information."""
        html = self.send_request("get", self.URL_PAYMENTS_PAGE, logfile=self._Log4)
        return PaymentsPageParser.parse_claim_payments(html)

    def send_request(self, method: str, url: str, **kwargs) -> str:
        """Send HTTP request."""
        try:
            logfile = kwargs.pop("logfile", None)
            http_method = getattr(self.session, method)
        except AttributeError as err:
            raise ByFlyError(f"Invalid method {method}") from err

        try:
            r = http_method(url, **kwargs)
            if r.status_code != 200:
                raise ByFlyInvalidResponseError(f"Page status code is {r.status_code}")
            html = r.text
            if logfile:
                log_to_file(logfile, html)
        except Exception as err:
            raise ByFlyInvalidResponseError(get_exception_str(err)) from err
        return html

    def get_money_measure(self) -> str:
        """Get money measurement unit."""
        return MONEY_MEASURE

    def get_traf_measure(self) -> str:
        """Get traffic measurement unit."""
        return TRAF_MEASURE


class PageParser:
    """Base HTML parser class."""

    STRIP_CHARS = ": \r\n"
    TAGS_RE = re.compile("<[^<]+?>")

    @classmethod
    def get_table_dict(cls, html: str) -> dict:
        """Extract table data as dictionary."""
        k = {}
        matches = re.findall(
            r"<tr[^>]*>[^<]*<td[^>]*>(.*?)</td[^>]*>[^<]*<td[^>]*>(.*?)</td[^>]*>[^<]*</tr>",
            html,
            re.DOTALL,
        )
        for match in matches:
            key = cls._clean_text(match[0])
            value = cls._clean_text(match[1])
            k[key] = value
        return k

    @classmethod
    def _clean_text(cls, text: str) -> str:
        """Clean HTML text by removing tags and stripping characters."""
        text = re.sub(cls.TAGS_RE, "", text)
        return text.strip(cls.STRIP_CHARS)

    @classmethod
    def strip_number_field(cls, s: str) -> Decimal:
        """Extract numeric value from string."""
        res = ""
        for char in s:
            if char.isdigit() or char in ["-", ",", "."]:
                res += char
            else:
                break
        res = res.replace(",", ".")
        return Decimal(res)

    @classmethod
    def get_tables(cls, html: str) -> list[list[list[str]]]:
        """Extract all tables from HTML."""
        TABLE_RE = r"<table[^>]*>.*?</table[^>]*>"
        matches = re.findall(TABLE_RE, html, re.DOTALL)
        return [cls.get_row(match) for match in matches]

    @classmethod
    def get_row(cls, table_html: str) -> list[list[str]]:
        """Extract rows from table HTML."""
        ROW_RE = r"<tr[^>]*>.*?</tr[^>]*>"
        matches = re.findall(ROW_RE, table_html, re.DOTALL)
        return [cls.get_cell(match) for match in matches]

    @classmethod
    def get_cell(cls, table_html: str) -> list[str]:
        """Extract cells from row HTML."""
        CELL_RE = r"<td[^>]*>(.*?)</td[^>]*>"
        matches = re.findall(CELL_RE, table_html, re.DOTALL)
        return [cls.strip_tags(match) for match in matches]

    @classmethod
    def strip_tags(cls, html: str) -> str:
        """Remove HTML tags from string."""
        return re.sub(cls.TAGS_RE, "", html)


class AccountPageParser(PageParser):
    """Parser for account information page."""

    FULL_NAME_KEY = "Абонент"
    PLAN_KEY = "Тарифный план на услуги"
    BALANCE_REGEXPR_PATTERN = r"Актуальный баланс: <b>(.*)</b>"

    @classmethod
    def parse_user_info(cls, html: str) -> Optional[UserInfo]:
        """Parse user information from account page."""
        balance = cls.parse_balance(html)
        if not balance:
            return None
        table_k = cls.get_table_dict(html)
        plan = table_k.get(cls.PLAN_KEY, "")
        full_name = table_k.get(cls.FULL_NAME_KEY, "")
        return UserInfo(full_name, plan, balance)

    @classmethod
    def parse_balance(cls, html: str) -> Optional[Decimal]:
        """Parse balance from account page."""
        m = re.search(cls.BALANCE_REGEXPR_PATTERN, html)
        if m:
            s = m.group(1).strip(" .")
            s = cls.strip_number_field(s)
            try:
                return Decimal(s)
            except Exception as e:
                logger.exception(get_exception_str(e))
                logger.debug("Не определен баланс")
                return None


class StatPageParser(PageParser):
    """Parser for statistics page."""

    TABLE_RE = r'<table[^>]* class="content">.*?</table>'
    ROW_RE = r"<tr[^>]*>(.*?)</tr>"
    CELL_RE = r"<td[^>]*>(.*?)</td>"
    DATE_FORMAT = "%d.%m.%Y  %H:%M:%S"

    KEY_SUM_COST = "Сумма"
    KEY_SUM_TRAF = "Суммарный трафик"

    @staticmethod
    def parse_html(html: str) -> list[Session]:
        """Parse sessions from statistics page."""
        table_html = StatPageParser.get_table(html)
        if not table_html:
            return []
        return [
            StatPageParser.parse_session(StatPageParser.parse_row(row))
            for row in StatPageParser.get_rows(table_html)
        ]

    @staticmethod
    def get_table(html: str) -> Optional[str]:
        """Get the statistics table from HTML."""
        tables = re.findall(StatPageParser.TABLE_RE, html, re.DOTALL)
        if not tables or len(tables) < 2:
            return None
        return tables[1]

    @staticmethod
    def get_rows(table_html: str) -> list[str]:
        """Get data rows from table HTML."""
        rows = re.findall(StatPageParser.ROW_RE, table_html, re.DOTALL)
        if not rows or len(rows) < 2:
            return []
        return rows[1:]

    @staticmethod
    def parse_row(row_html: str) -> Optional[list[str]]:
        """Parse cells from row HTML."""
        cells = re.findall(StatPageParser.CELL_RE, row_html, re.DOTALL)
        if not cells:
            return None
        return cells

    @staticmethod
    def parse_session(row_cells: list[str]) -> Optional[Session]:
        """Parse session data from row cells."""
        if len(row_cells) != 7:
            return None

        try:
            raw_title = row_cells[0]
            raw_begin = row_cells[1]
            raw_end = row_cells[2]
            raw_duration = row_cells[3]
            raw_ingoing = row_cells[4]
            raw_outgoing = row_cells[5]
            raw_cost = row_cells[6]

            title = raw_title.strip()
            begin = datetime.strptime(raw_begin, StatPageParser.DATE_FORMAT)
            end = datetime.strptime(raw_end, StatPageParser.DATE_FORMAT)

            duration = StatPageParser._parse_duration(raw_duration)

            ingoing = float(raw_ingoing)
            outgoing = float(raw_outgoing)
            cost = Decimal(raw_cost)

            return Session(title, begin, end, duration, ingoing, outgoing, cost)
        except Exception as e:
            print(e)
            return None

    @staticmethod
    def _parse_duration(raw_duration: str) -> timedelta:
        """Parse duration string to timedelta."""
        try:
            ttuple = time.strptime(raw_duration, "%d.%H:%M:%S")[2:6]
            return timedelta(days=ttuple[0], hours=ttuple[1], minutes=ttuple[2], seconds=ttuple[3])
        except Exception:
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
            return timedelta(hours=hours, minutes=minutes, seconds=seconds)

    @classmethod
    def parse_total_stat_info(cls, html: str) -> Optional[TotalStatInfo]:
        """Parse total statistics from page."""
        if not html:
            return None
        try:
            d = cls.get_table_dict(html)
            cost = d.get(cls.KEY_SUM_COST, "")
            traf = d.get(cls.KEY_SUM_TRAF, "")
            cost = cls.strip_number_field(cost)
            traf = cls.strip_number_field(traf)
            return TotalStatInfo(traf, cost)
        except Exception:
            return None


class PaymentsPageParser(PageParser):
    """Parser for payments page."""

    @classmethod
    def parse_claim_payments(cls, html: str) -> list[ClaimPayment]:
        """Parse claim payments from page."""
        claim_payments = []
        tables = cls.get_tables(html)
        for table in tables:
            if len(table) > 0:
                row = table[0]
                if len(row) > 0 and row[0].startswith("Зачисленные обещанные платежи"):
                    if len(table) > 2:
                        for row in table[2:]:
                            if len(row) != 5:
                                continue
                            is_active = row[3] == "Активен"
                            try:
                                cost = cls.strip_number_field(row[2])
                            except Exception:
                                cost = Decimal("0")
                            claim_payments.append(
                                ClaimPayment(row[0], row[1], is_active, cost, row[4])
                            )
        return claim_payments
