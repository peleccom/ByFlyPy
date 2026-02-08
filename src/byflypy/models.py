"""Shared data models for ByFlyPy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class Session:
    """Internet session data (legacy format for backwards compatibility)."""

    title: str
    begin: datetime
    end: datetime
    duration: timedelta
    ingoing: float
    outgoing: float
    cost: Decimal

    def __str__(self) -> str:
        return f"Session<{self.begin}  {self.end}>"


@dataclass(frozen=True)
class UserInfo:
    """User account information."""

    full_name: str
    plan: str
    balance: Decimal


@dataclass(frozen=True)
class TotalStatInfo:
    """Total statistics information."""

    total_traf: Decimal
    total_cost: Decimal


@dataclass(frozen=True)
class ClaimPayment:
    """Claim payment information."""

    pk: str
    date: str
    is_active: bool
    cost: Decimal
    type_of_payment: str


@dataclass(frozen=True)
class TrafficSession:
    """Traffic session from API v2."""

    start: datetime
    stop: datetime
    time_on: str
    in_trf: float
    out_trf: float
    sum_trf: float
    num: str

    def to_legacy_session(self) -> Session:
        """Convert to legacy Session format for plotting compatibility."""
        duration = parse_duration(self.time_on)

        return Session(
            title=self.num,
            begin=self.start,
            end=self.stop,
            duration=duration,
            ingoing=self.in_trf,
            outgoing=self.out_trf,
            cost=Decimal("0"),
        )


@dataclass(frozen=True)
class TrafficDetails:
    """Traffic statistics for a contract/application."""

    total_incoming: Decimal
    total_outgoing: Decimal
    total_traffic: Decimal
    total_duration: str
    sessions: list[Session]

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> TrafficDetails | None:
        """Create TrafficDetails from API response."""
        call_accum = data.get("call_accum")
        if not call_accum:
            return None

        inetstat = data.get("inetstat", [])
        sessions = []
        for session_data in inetstat:
            try:
                ts = TrafficSession(
                    start=datetime.strptime(session_data["start"], "%d.%m.%Y %H:%M:%S"),
                    stop=datetime.strptime(session_data["stop"], "%d.%m.%Y %H:%M:%S"),
                    time_on=session_data["time_on"],
                    in_trf=float(session_data["in_trf"]),
                    out_trf=float(session_data["out_trf"]),
                    sum_trf=float(session_data["sum_trf"]),
                    num=session_data.get("num", "Traffic"),
                )
                sessions.append(ts.to_legacy_session())
            except (KeyError, ValueError):
                continue

        return cls(
            total_incoming=Decimal(str(call_accum.get("in_trf", 0))),
            total_outgoing=Decimal(str(call_accum.get("out_trf", 0))),
            total_traffic=Decimal(str(call_accum.get("sum_trf", 0))),
            total_duration=call_accum.get("dur_trf_txt", "0:00:00"),
            sessions=sessions,
        )


def parse_duration(time_str: str) -> timedelta:
    """Parse duration string to timedelta.

    Handles formats:
    - "HH:MM:SS"
    - "DDD:HH:MM:SS" (days:hours:minutes:seconds)
    """
    parts = time_str.split(":")
    if len(parts) == 3:
        hours, minutes, seconds = map(int, parts)
        return timedelta(hours=hours, minutes=minutes, seconds=seconds)
    elif len(parts) == 4:
        days, hours, minutes, seconds = map(int, parts)
        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    else:
        return timedelta()
