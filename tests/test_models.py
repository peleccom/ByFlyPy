"""Tests for ByFlyPy models."""

from datetime import datetime, timedelta
from decimal import Decimal

from byflypy.models import (
    ClaimPayment,
    Session,
    TotalStatInfo,
    TrafficDetails,
    TrafficSession,
    UserInfo,
    parse_duration,
)


class TestSession:
    """Test Session dataclass."""

    def test_session_creation(self):
        """Test creating a Session object."""
        begin = datetime(2026, 2, 1, 10, 0, 0)
        end = datetime(2026, 2, 1, 11, 0, 0)
        duration = timedelta(hours=1)

        session = Session(
            title="Test Session",
            begin=begin,
            end=end,
            duration=duration,
            ingoing=100.5,
            outgoing=50.3,
            cost=Decimal("10.00"),
        )

        assert session.title == "Test Session"
        assert session.begin == begin
        assert session.end == end
        assert session.duration == duration
        assert session.ingoing == 100.5
        assert session.outgoing == 50.3
        assert session.cost == Decimal("10.00")

    def test_session_str(self):
        """Test Session string representation."""
        begin = datetime(2026, 2, 1, 10, 0, 0)
        end = datetime(2026, 2, 1, 11, 0, 0)
        session = Session(
            title="Test",
            begin=begin,
            end=end,
            duration=timedelta(hours=1),
            ingoing=0,
            outgoing=0,
            cost=Decimal("0"),
        )
        assert "2026-02-01 10:00:00" in str(session)


class TestTrafficSession:
    """Test TrafficSession dataclass."""

    def test_traffic_session_creation(self):
        """Test creating a TrafficSession object."""
        start = datetime(2026, 2, 1, 10, 0, 0)
        stop = datetime(2026, 2, 1, 11, 0, 0)

        ts = TrafficSession(
            start=start,
            stop=stop,
            time_on="1:00:00",
            in_trf=100.5,
            out_trf=50.3,
            sum_trf=150.8,
            num="Traffic",
        )

        assert ts.start == start
        assert ts.stop == stop
        assert ts.time_on == "1:00:00"
        assert ts.in_trf == 100.5

    def test_to_legacy_session(self):
        """Test conversion to legacy Session format."""
        start = datetime(2026, 2, 1, 10, 0, 0)
        stop = datetime(2026, 2, 1, 11, 30, 0)

        ts = TrafficSession(
            start=start,
            stop=stop,
            time_on="1:30:00",
            in_trf=100.0,
            out_trf=50.0,
            sum_trf=150.0,
            num="Traffic",
        )

        legacy = ts.to_legacy_session()
        assert isinstance(legacy, Session)
        assert legacy.title == "Traffic"
        assert legacy.begin == start
        assert legacy.end == stop
        assert legacy.ingoing == 100.0
        assert legacy.outgoing == 50.0
        assert legacy.cost == Decimal("0")


class TestTrafficDetails:
    """Test TrafficDetails dataclass."""

    def test_from_api_response(self):
        """Test creating TrafficDetails from API response."""
        api_response = {
            "traffic_type": "data",
            "login": "test_login",
            "call_accum": {
                "in_trf": 119233.253,
                "out_trf": 20872.497,
                "sum_trf": 140105.75,
                "dur_trf_txt": "181:47:47",
            },
            "inetstat": [
                {
                    "start": "01.02.2026 02:39:13",
                    "stop": "01.02.2026 16:07:00",
                    "time_on": "13:27:47",
                    "in_trf": 2455.767,
                    "out_trf": 641.925,
                    "sum_trf": 3097.692,
                    "num": "Traffic",
                }
            ],
        }

        details = TrafficDetails.from_api_response(api_response)
        assert details is not None
        assert details.total_incoming == Decimal("119233.253")
        assert details.total_outgoing == Decimal("20872.497")
        assert details.total_traffic == Decimal("140105.75")
        assert details.total_duration == "181:47:47"
        assert len(details.sessions) == 1

    def test_from_api_response_empty(self):
        """Test handling empty API response."""
        result = TrafficDetails.from_api_response({})
        assert result is None

    def test_from_api_response_no_sessions(self):
        """Test API response with no sessions."""
        api_response = {
            "call_accum": {
                "in_trf": 100.0,
                "out_trf": 50.0,
                "sum_trf": 150.0,
                "dur_trf_txt": "1:00:00",
            },
            "inetstat": [],
        }

        details = TrafficDetails.from_api_response(api_response)
        assert details is not None
        assert len(details.sessions) == 0


class TestParseDuration:
    """Test parse_duration helper function."""

    def test_parse_duration_hours_only(self):
        """Test parsing HH:MM:SS format."""
        result = parse_duration("13:27:47")
        assert result == timedelta(hours=13, minutes=27, seconds=47)

    def test_parse_duration_with_days(self):
        """Test parsing DDD:HH:MM:SS format."""
        result = parse_duration("120:00:00")
        # This format is actually HH:MM:SS where hours can be > 24
        # Our parser treats 4 parts as days:hours:minutes:seconds
        result = parse_duration("5:00:00:00")
        assert result == timedelta(days=5)

    def test_parse_duration_invalid(self):
        """Test parsing invalid format."""
        result = parse_duration("invalid")
        assert result == timedelta()


class TestUserInfo:
    """Test UserInfo dataclass."""

    def test_user_info_creation(self):
        """Test creating UserInfo object."""
        info = UserInfo(
            full_name="Иванов Иван Иванович",
            plan="ЯСНА 100",
            balance=Decimal("100.50"),
        )
        assert info.full_name == "Иванов Иван Иванович"
        assert info.plan == "ЯСНА 100"
        assert info.balance == Decimal("100.50")


class TestTotalStatInfo:
    """Test TotalStatInfo dataclass."""

    def test_total_stat_info_creation(self):
        """Test creating TotalStatInfo object."""
        info = TotalStatInfo(
            total_traf=Decimal("1000.5"),
            total_cost=Decimal("50.00"),
        )
        assert info.total_traf == Decimal("1000.5")
        assert info.total_cost == Decimal("50.00")


class TestClaimPayment:
    """Test ClaimPayment dataclass."""

    def test_claim_payment_creation(self):
        """Test creating ClaimPayment object."""
        payment = ClaimPayment(
            pk="123",
            date="01.02.2026",
            is_active=True,
            cost=Decimal("20.00"),
            type_of_payment="Обещанный",
        )
        assert payment.pk == "123"
        assert payment.is_active is True
        assert payment.cost == Decimal("20.00")
