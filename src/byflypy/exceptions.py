"""Unified exception hierarchy for ByFlyPy."""

from __future__ import annotations

__all__ = [
    "ByFly2FARequiredError",
    "ByFlyAuthError",
    "ByFlyBanError",
    "ByFlyEmptyResponseError",
    "ByFlyError",
    "ByFlyInvalidResponseError",
]


class ByFlyError(Exception):
    """Base exception for ByFly-related errors."""


class ByFlyAuthError(ByFlyError):
    """Raised when authentication fails."""


class ByFly2FARequiredError(ByFlyError):
    """Raised when SMS 2FA is required."""


class ByFlyBanError(ByFlyError):
    """Raised when too many login attempts have been made."""


class ByFlyEmptyResponseError(ByFlyError):
    """Raised when server returns an empty response."""


class ByFlyInvalidResponseError(ByFlyError):
    """Raised when server returns an invalid response."""
