"""Protocol for ByFly clients used by the UI layer."""

from __future__ import annotations

from typing import Protocol


class ByFlyClientProtocol(Protocol):
    """Protocol for ByFly clients. UI branches on api_version instead of type."""

    @property
    def api_version(self) -> int:
        """1 = HTML/scraping API, 2 = REST API."""
        ...
