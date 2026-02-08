"""Tests for ByFlyPy API client."""

from decimal import Decimal

import pytest
import requests_mock

from byflypy.api_client import (
    ApiApplication,
    ApiContract,
    ApiUser,
    ByFly2FARequiredError,
    ByFlyApiClient,
    ByFlyAuthError,
    ByFlyError,
)


class TestByFlyApiClient:
    """Test ByFlyApiClient class."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return ByFlyApiClient("375331234567", "testpass")

    @pytest.fixture
    def mock_auth_response(self):
        """Mock successful auth response."""
        return {
            "2fa": False,
            "access_token": "test_token_123",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

    def test_init(self, client):
        """Test client initialization."""
        assert client._phone == "375331234567"
        assert client._password == "testpass"
        assert client._access_token is None

    def test_set_sms_code(self, client):
        """Test setting SMS code."""
        client.set_sms_code("123456")
        assert client._sms_code == "123456"

    def test_set_access_token(self, client):
        """Test setting access token."""
        client.set_access_token("test_token")
        assert client.access_token == "test_token"
        assert client.is_authenticated is True

    def test_is_authenticated_no_token(self, client):
        """Test authentication check with no token."""
        assert client.is_authenticated is False

    def test_login_success(self, client, mock_auth_response):
        """Test successful login."""
        with requests_mock.Mocker() as m:
            m.post(
                "https://myapi.beltelecom.by/api/v2/oauth/token",
                json=mock_auth_response,
            )
            result = client.login()
            assert result is True
            assert client.access_token == "test_token_123"

    def test_login_2fa_required(self, client):
        """Test login requiring 2FA."""
        with requests_mock.Mocker() as m:
            m.post(
                "https://myapi.beltelecom.by/api/v2/oauth/token",
                json={"2fa": True},
            )
            with pytest.raises(ByFly2FARequiredError):
                client.login()

    def test_login_failure(self, client):
        """Test failed login."""
        with requests_mock.Mocker() as m:
            m.post(
                "https://myapi.beltelecom.by/api/v2/oauth/token",
                status_code=401,
            )
            with pytest.raises(ByFlyAuthError):
                client.login()

    def test_login_empty_credentials(self):
        """Test login with empty credentials."""
        client = ByFlyApiClient()
        with pytest.raises(ByFlyAuthError):
            client.login()


class TestApiContract:
    """Test ApiContract dataclass."""

    def test_from_dict(self):
        """Test creating ApiContract from dict."""
        data = {
            "id": 10845167,
            "user_id": 1144301,
            "login": "test_login",
            "balance": 47.49,
            "status": "complete",
            "name": "Иванов Иван",
            "addresses": "Test Address",
            "price": 41.5,
            "terminate_in": 34,
            "applications": [],
            "can_add_funds": True,
            "can_apply_promised_payment": True,
            "max_promised_payment_amount": "20.00",
        }

        contract = ApiContract.from_dict(data)
        assert contract.id == 10845167
        assert contract.balance == Decimal("47.49")
        assert contract.name == "Иванов Иван"

    def test_from_dict_missing_balance(self):
        """Test creating contract with missing balance."""
        data = {"id": 1, "login": "test"}
        contract = ApiContract.from_dict(data)
        assert contract.balance == Decimal("0")


class TestApiApplication:
    """Test ApiApplication dataclass."""

    def test_from_dict(self):
        """Test creating ApiApplication from dict."""
        data = {
            "id": 15305597,
            "tariff_id": 253,
            "price": "41.50",
            "tariff": {
                "id": 253,
                "name": "ЯСНА 100",
                "description": "Test tariff",
                "individual_price": "41.50",
                "is_archival": False,
            },
            "services": [],
            "can_change_tariff": True,
            "tariff_change_available_at": None,
            "available_tariffs": [],
            "btk_login": "test_login",
        }

        app = ApiApplication.from_dict(data)
        assert app.id == 15305597
        assert app.btk_login == "test_login"
        assert app.tariff is not None
        assert app.tariff.name == "ЯСНА 100"


class TestGetTrafficDetails:
    """Test get_traffic_details method."""

    @pytest.fixture
    def authenticated_client(self):
        """Create an authenticated client."""
        client = ByFlyApiClient("375331234567", "testpass")
        client.set_access_token("test_token")
        return client

    def test_get_traffic_details_success(self, authenticated_client):
        """Test successful traffic details fetch."""
        mock_response = {
            "traffic_type": "data",
            "call_accum": {
                "in_trf": 100.0,
                "out_trf": 50.0,
                "sum_trf": 150.0,
                "dur_trf_txt": "10:00:00",
            },
            "inetstat": [
                {
                    "start": "01.02.2026 10:00:00",
                    "stop": "01.02.2026 20:00:00",
                    "time_on": "10:00:00",
                    "in_trf": 100.0,
                    "out_trf": 50.0,
                    "sum_trf": 150.0,
                    "num": "Traffic",
                }
            ],
        }

        with requests_mock.Mocker() as m:
            m.post(
                "https://myapi.beltelecom.by/api/v2/contracts/123/applications/456/fetch-traffic-details",
                json=mock_response,
            )
            result = authenticated_client.get_traffic_details(123, 456)
            assert result is not None
            assert result.total_incoming == Decimal("100.0")
            assert len(result.sessions) == 1

    def test_get_traffic_details_failure(self, authenticated_client):
        """Test traffic details fetch failure."""
        with requests_mock.Mocker() as m:
            m.post(
                "https://myapi.beltelecom.by/api/v2/contracts/123/applications/456/fetch-traffic-details",
                status_code=500,
            )
            with pytest.raises(ByFlyError):
                authenticated_client.get_traffic_details(123, 456)


class TestGetInternetLogins:
    """Test get_internet_logins method."""

    @pytest.fixture
    def authenticated_client(self):
        """Create an authenticated client."""
        client = ByFlyApiClient("375331234567", "testpass")
        client.set_access_token("test_token")
        return client

    def test_get_internet_logins(self, authenticated_client):
        """Test getting internet logins."""
        mock_contract = {
            "id": 123,
            "applications": [
                {
                    "id": 456,
                    "btk_login": "login1",
                    "tariff_id": 1,
                    "price": "41.50",
                    "tariff": {
                        "id": 1,
                        "name": "ЯСНА 100",
                        "individual_price": "41.50",
                    },
                    "services": [],
                    "can_change_tariff": False,
                    "available_tariffs": [],
                },
                {
                    "id": 789,
                    "btk_login": "login2",
                    "tariff_id": 2,
                    "price": "46.00",
                    "tariff": {
                        "id": 2,
                        "name": "ЯСНА 200",
                        "individual_price": "46.00",
                    },
                    "services": [],
                    "can_change_tariff": False,
                    "available_tariffs": [],
                },
            ],
        }

        with requests_mock.Mocker() as m:
            m.get(
                "https://myapi.beltelecom.by/api/v2/contracts/123",
                json=mock_contract,
            )
            logins = authenticated_client.get_internet_logins(123)
            assert len(logins) == 2
            assert logins[0]["login"] == "login1"
            assert logins[1]["login"] == "login2"

    def test_get_internet_logins_empty(self, authenticated_client):
        """Test getting internet logins with empty applications."""
        mock_contract = {
            "id": 123,
            "applications": [],
        }

        with requests_mock.Mocker() as m:
            m.get(
                "https://myapi.beltelecom.by/api/v2/contracts/123",
                json=mock_contract,
            )
            logins = authenticated_client.get_internet_logins(123)
            assert len(logins) == 0


class TestApiUser:
    """Test ApiUser dataclass."""

    def test_from_dict(self):
        """Test creating ApiUser from dict."""
        data = {
            "id": 1144301,
            "phone": "375331234567",
            "email": "test@example.com",
            "name": "Иванов Иван",
            "language": "ru",
            "is_email_verified": True,
            "is_sms_2fa_enabled": True,
            "created_at": "2018-04-29 22:46:14",
            "contracts_count": 2,
        }

        user = ApiUser.from_dict(data)
        assert user.id == 1144301
        assert user.phone == "375331234567"
        assert user.name == "Иванов Иван"
        assert user.contracts_count == 2
