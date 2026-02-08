"""Pytest configuration for ByFlyPy tests."""

import pytest


@pytest.fixture
def mock_session():
    """Create a mock session for testing."""
    from datetime import datetime, timedelta
    from decimal import Decimal

    from byflypy.models import Session

    return Session(
        title="Test Session",
        begin=datetime(2026, 2, 1, 10, 0, 0),
        end=datetime(2026, 2, 1, 11, 0, 0),
        duration=timedelta(hours=1),
        ingoing=100.5,
        outgoing=50.3,
        cost=Decimal("0"),
    )
