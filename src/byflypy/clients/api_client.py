"""New REST API v2 client for Beltelecom ByFly."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import requests

from byflypy.exceptions import (
    ByFly2FARequiredError,
    ByFlyAuthError,
    ByFlyError,
)
from byflypy.models import (
    TrafficDetails,
)

if TYPE_CHECKING:
    from typing import Any

    from byflypy.console import Console

HTTP_METHODS_LITERAL = Literal["GET", "POST"]

logger = logging.getLogger(__name__)

__all__ = [
    "ApiApplication",
    "ApiAuthResult",
    "ApiContract",
    "ApiService",
    "ApiTariff",
    "ApiUser",
    "ByFly2FARequiredError",
    "ByFlyApiClient",
    "TokenManager",
]


class TokenManager:
    """Manage access tokens for API v2."""

    def __init__(
        self,
        token_file: Path | None = None,
        console: Console | None = None,
    ) -> None:
        self._token_file = token_file or Path.home() / ".byfly_token.json"
        self._console = console

    def load(self, phone: str) -> str | None:
        """Load access token from file for given phone number."""
        if not self._token_file.exists():
            return None

        try:
            with open(self._token_file) as f:
                data = json.load(f)
            profile = data.get(phone)
            if not profile:
                return None

            access_token = profile.get("access_token")
            expires_at_str = profile.get("expires_at")

            if not access_token:
                return None

            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now() >= expires_at:
                    if self._console:
                        self._console.print(f"Token for {phone} has expired")
                    else:
                        print(f"Token for {phone} has expired")
                    return None
        except (json.JSONDecodeError, ValueError, OSError):
            return None
        else:
            return access_token

    def save(self, phone: str, access_token: str, expires_at: datetime | None = None) -> None:
        """Save access token to file for given phone number."""
        data: dict[str, dict[str, Any]] = {}

        if self._token_file.exists():
            try:
                with open(self._token_file) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, ValueError):
                data = {}

        data[phone] = {
            "access_token": access_token,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "phone": phone,
        }

        with open(self._token_file, "w") as f:
            json.dump(data, f, indent=2)

        if self._console:
            self._console.print(f"Token saved to {self._token_file}")
        else:
            print(f"Token saved to {self._token_file}")


def _to_decimal(value: str | int | float | None) -> Decimal:
    """Convert value to Decimal safely."""
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


@dataclass(frozen=True)
class ApiAuthResult:
    """OAuth authentication result."""

    requires_2fa: bool
    access_token: str | None
    expires_in: int | None
    token_type: str | None


@dataclass(frozen=True)
class ApiTariff:
    """Tariff details."""

    id: int
    name: str
    description: str
    price: Decimal
    group_name: str | None
    is_archival: bool

    @classmethod
    def from_dict(cls, data: dict) -> ApiTariff:
        """Create ApiTariff from API response dict."""
        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            description=data.get("description", "") or "",
            price=_to_decimal(data.get("individual_price")),
            group_name=data.get("group", {}).get("name") if data.get("group") else None,
            is_archival=bool(data.get("is_archival", False)),
        )


@dataclass(frozen=True)
class ApiService:
    """Active service on contract."""

    id: int
    name: str
    description: str | None
    price: Decimal
    period: str
    is_removable: bool

    @classmethod
    def from_dict(cls, data: dict) -> ApiService:
        """Create ApiService from API response dict."""
        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            description=data.get("description"),
            price=_to_decimal(data.get("individual_price")),
            period=data.get("period", "month"),
            is_removable=bool(data.get("removable", False)),
        )


@dataclass(frozen=True)
class ApiApplication:
    """Contract application (tariff subscription)."""

    id: int
    tariff_id: int
    price: Decimal
    tariff: ApiTariff | None
    services: list[ApiService]
    can_change_tariff: bool
    tariff_change_available_at: str | None
    available_tariffs: list[ApiTariff]
    btk_login: str

    @classmethod
    def from_dict(cls, data: dict) -> ApiApplication:
        """Create ApiApplication from API response dict."""
        tariff_data = data.get("tariff")
        tariff = ApiTariff.from_dict(tariff_data) if tariff_data else None

        services = [ApiService.from_dict(s) for s in data.get("services", [])]

        available = data.get("available_tariffs", [])
        available_tariffs = [ApiTariff.from_dict(t) for t in available]

        return cls(
            id=data.get("id", 0),
            tariff_id=data.get("tariff_id", 0),
            price=_to_decimal(data.get("price")),
            tariff=tariff,
            services=services,
            can_change_tariff=bool(data.get("can_change_tariff", False)),
            tariff_change_available_at=data.get("tariff_change_available_at"),
            available_tariffs=available_tariffs,
            btk_login=data.get("btk_login", ""),
        )


@dataclass(frozen=True)
class ApiContract:
    """Contract (account) from /contracts or /contracts/{id}."""

    id: int
    user_id: int
    login: str
    btk_id: str
    balance: Decimal
    status: str
    name: str
    addresses: str | None
    price: Decimal
    terminate_in: int | None
    applications: list[ApiApplication]
    can_add_funds: bool
    can_apply_promised_payment: bool
    max_promised_payment_amount: Decimal | None

    @classmethod
    def from_dict(cls, data: dict) -> ApiContract:
        """Create ApiContract from API response dict."""
        raw_balance = data.get("balance")
        balance = _to_decimal(raw_balance)

        raw_max_payment = data.get("max_promised_payment_amount")
        max_payment = _to_decimal(raw_max_payment) if raw_max_payment is not None else None

        applications = [ApiApplication.from_dict(a) for a in data.get("applications", [])]

        return cls(
            id=data.get("id", 0),
            user_id=data.get("user_id", 0),
            login=data.get("login", ""),
            btk_id=data.get("btk_id", ""),
            balance=balance,
            status=data.get("status", ""),
            name=data.get("name", ""),
            addresses=data.get("addresses"),
            price=_to_decimal(data.get("price")),
            terminate_in=data.get("terminate_in"),
            applications=applications,
            can_add_funds=bool(data.get("can_add_funds", False)),
            can_apply_promised_payment=bool(data.get("can_apply_promised_payment", False)),
            max_promised_payment_amount=max_payment,
        )


@dataclass(frozen=True)
class ApiUser:
    """User profile from /users/self."""

    id: int
    phone: str
    email: str
    name: str
    language: str
    is_email_verified: bool
    is_sms_2fa_enabled: bool
    created_at: datetime
    region_code: str | None
    contracts_count: int

    @classmethod
    def from_dict(cls, data: dict) -> ApiUser:
        """Create ApiUser from API response dict."""
        raw_created = data.get("created_at", "")
        try:
            created_at = datetime.strptime(raw_created, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            created_at = datetime.now()

        return cls(
            id=data.get("id", 0),
            phone=data.get("phone", ""),
            email=data.get("email", ""),
            name=data.get("name", ""),
            language=data.get("language", "ru"),
            is_email_verified=bool(data.get("is_email_verified", False)),
            is_sms_2fa_enabled=bool(data.get("is_sms_2fa_enabled", False)),
            created_at=created_at,
            region_code=data.get("region_code"),
            contracts_count=data.get("contracts_count", 0),
        )


class ByFlyApiClient:
    """REST API v2 client for Beltelecom ByFly.

    Usage:
        client = ByFlyApiClient("375334444444", "mypassword")
        try:
            client.login()
        except ByFly2FARequiredError:
            code = input("Enter SMS code: ")
            client.set_sms_code(code)
            client.login()

        contracts = client.get_contracts()
        for contract in contracts:
            print(f"{contract.name}: {contract.balance}")
    """

    api_version = 2  # REST API v2
    BASE_URL = "https://myapi.beltelecom.by/api/v2"

    def __init__(
        self,
        phone: str | None = None,
        password: str | None = None,
        sms_code: str | None = None,
        login: str | None = None,
        token_manager: TokenManager | None = None,
    ) -> None:
        """Initialize API client.

        Args:
            phone: Phone number (e.g., "375334444444"). Optional if using access_token.
            password: Account password. Optional if using access_token.
            sms_code: SMS 2FA code (required after first login if enabled)
            login: Login number (contract ID) to use
            token_manager: Optional TokenManager for automatic token persistence
        """
        self._phone = phone
        self._password = password
        self._sms_code = sms_code
        self._login = login
        self._token_manager = token_manager
        self._session = requests.Session()
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None
        self._user: ApiUser | None = None

    def set_sms_code(self, sms_code: str) -> None:
        """Set SMS 2FA code."""
        self._sms_code = sms_code

    def set_access_token(self, access_token: str) -> None:
        """Set access token directly (skip login)."""
        self._access_token = access_token

    def _normalize_phone(self, phone: str) -> str:
        return phone.replace("+", "").replace(" ", "")

    @property
    def access_token(self) -> str | None:
        """Get the current access token."""
        return self._access_token

    @property
    def is_authenticated(self) -> bool:
        """Check if client has valid authentication."""
        if not self._access_token:
            return False
        return not (self._token_expires_at and datetime.now() >= self._token_expires_at)

    def login(self, use_saved_token: bool = True) -> bool:
        """Authenticate with the API.

        Args:
            use_saved_token: If True and token_manager is set, try to load saved token first

        Returns:
            True if login successful

        Raises:
            ByFly2FARequiredError: If SMS code needed but not provided
            ByFlyAuthError: If authentication fails
        """
        if use_saved_token and self._token_manager and self._phone:
            saved_token = self._token_manager.load(self._phone)
            if saved_token:
                self._access_token = saved_token
                self.get_user()
                return True

        if not self._phone or not self._password:
            raise ByFlyAuthError("Empty phone or password")

        result = self._request_token()

        if result.requires_2fa:
            raise ByFly2FARequiredError(
                "SMS code required. Check your phone and provide --sms-code"
            )

        if not result.access_token:
            raise ByFlyAuthError("Failed to obtain access token")
        print(f"Access token: {result.access_token}")

        self._access_token = result.access_token
        if result.expires_in:
            self._token_expires_at = datetime.now() + timedelta(seconds=result.expires_in)

        if self._token_manager and self._phone:
            self._token_manager.save(self._phone, self._access_token, self._token_expires_at)

        return True

    def _request_token(self) -> ApiAuthResult:
        """Make OAuth token request."""
        payload: dict = {
            "username": self._normalize_phone(self._phone),  # type: ignore[arg-type]
            "password": self._password,
        }

        if self._sms_code:
            payload["code"] = self._sms_code

        resp = self._make_request(
            "POST",
            "oauth/token",
            payload=payload,
            auth=False,
        )
        if resp.status_code != 200:
            raise ByFlyAuthError(
                f"Authentication failed with status {resp.status_code}.\n {resp.text}"
            )
        data = resp.json()
        return ApiAuthResult(
            requires_2fa=data.get("2fa", False),
            access_token=data.get("access_token"),
            expires_in=data.get("expires_in"),
            token_type=data.get("token_type"),
        )

    def _base_headers(self) -> dict:
        """Get base headers for API requests."""
        return {
            "accept": "application/json",
            "content-type": "application/json",
            "hl": "ru",
            "origin": "https://my.beltelecom.by",
            "referer": "https://my.beltelecom.by/",
            "x-client": "web",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        }

    def _make_request(
        self, method: HTTP_METHODS_LITERAL, api_path: str, payload: dict | None = None, auth=True
    ) -> requests.Response:
        if api_path.startswith("/"):
            api_path = api_path[1:]
        headers = self._auth_headers() if auth else self._base_headers()
        resp = self._session.request(
            method=method, url=f"{self.BASE_URL}/{api_path}", headers=headers, json=payload
        )
        if resp.status_code == 401:
            raise ByFlyAuthError(f"Authentication failed {resp.text}")
        return resp

    def _auth_headers(self) -> dict:
        """Get authenticated headers."""
        if not self._access_token:
            raise ByFlyError("Not authenticated. Call login() first.")
        return {
            **self._base_headers(),
            "authorization": f"Bearer {self._access_token}",
        }

    def _ensure_authenticated(self) -> None:
        """Ensure we have valid authentication."""
        if not self.is_authenticated:
            if not self._access_token:
                self.login()
            else:
                raise ByFlyError("Not authenticated. Call login() first.")

    def get_user(self) -> ApiUser:
        """Get current user profile."""
        self._ensure_authenticated()
        resp = self._make_request(
            "GET",
            "users/self",
        )

        if resp.status_code != 200:
            raise ByFlyError(f"Failed to get user: status {resp.status_code}")

        data = resp.json()
        self._user = ApiUser.from_dict(data)
        return self._user

    def get_contracts(self) -> list[ApiContract]:
        """List all contracts for user."""
        self._ensure_authenticated()

        resp = self._make_request(
            "GET",
            "contracts",
        )

        if resp.status_code != 200:
            raise ByFlyError(f"Failed to get contracts: status {resp.status_code}")

        data = resp.json()
        contracts_data = data.get("data", [])
        return [ApiContract.from_dict(c) for c in contracts_data]

    def get_contract(self, contract_id: int) -> ApiContract:
        """Get single contract by ID."""
        self._ensure_authenticated()

        resp = self._make_request(
            "GET",
            f"/contracts/{contract_id}",
        )

        if resp.status_code != 200:
            raise ByFlyError(f"Failed to get contract {contract_id}: status {resp.status_code}")

        data = resp.json()
        contract_data = data.get("contract", data)
        return ApiContract.from_dict(contract_data)

    def get_primary_contract(self) -> ApiContract | None:
        """Get the primary contract (uses _login if set, otherwise first)."""
        if self._login:
            contracts = self.get_contracts()
            for contract in contracts:
                if contract.login == self._login:
                    return contract
            return None
        contracts = self.get_contracts()
        return contracts[0] if contracts else None

    def get_traffic_details(
        self,
        contract_id: int,
        application_id: int,
    ) -> TrafficDetails | None:
        """Fetch traffic statistics for an application.

        Tries to call the API without usage-details-key first.

        Args:
            contract_id: The contract ID
            application_id: The application ID

        Returns:
            TrafficDetails object or None if failed
        """
        self._ensure_authenticated()

        # Try without usage-details-key first

        resp = self._make_request(
            "POST",
            f"contracts/{contract_id}/applications/{application_id}/fetch-traffic-details",
            payload={"attach_file": False},
        )

        if resp.status_code != 200:
            raise ByFlyError(f"Failed to get traffic details: status {resp.status_code}")

        data = resp.json()
        return TrafficDetails.from_api_response(data)
