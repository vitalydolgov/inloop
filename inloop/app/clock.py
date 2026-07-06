"""Port for reading the current date."""

from datetime import date
from typing import Protocol


class Clock(Protocol):
    """Reports the current calendar date."""

    def today(self) -> date:
        """Return today's date."""
        ...
