"""Console I/O abstraction for testability and isolation."""

from __future__ import annotations

import getpass as _getpass
from typing import Protocol


class Console(Protocol):
    """Protocol for console input/output. Inject a mock in tests."""

    def print(self, msg: str, end: str = "\n") -> None:
        """Print a message."""
        ...

    def input(self, prompt: str = "") -> str:
        """Read a line of input."""
        ...

    def get_password(self, prompt: str = "Password:") -> str:
        """Read a password without echoing."""
        ...

    def input_yn(self, prompt: str = "") -> bool | None:
        """Read yn value."""
        ...


class StdioConsole:
    """Default console using stdin/stdout and getpass."""

    def print(self, msg: str, end: str = "\n") -> None:
        print(msg, end=end)

    def input(self, prompt: str = "") -> str:
        return input(prompt)

    def get_password(self, prompt: str = "Password:") -> str:
        try:
            return _getpass.getpass(prompt, echo_char="*")  # type: ignore[call-arg]
        except TypeError:
            return _getpass.getpass(prompt, stream=None)

    def input_yn(self, prompt: str = "") -> bool | None:
        v = input(prompt).lower()
        if v in ["y", "yes"]:
            return True
        if v in ["n", "no"]:
            return False


def default_console() -> StdioConsole:
    """Return the default stdio-based console."""
    return StdioConsole()
