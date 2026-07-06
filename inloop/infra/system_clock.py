"""Clock backed by the operating system's calendar."""

from datetime import date


class SystemClock:
    """A Clock that reads today's date from the operating system."""

    def today(self) -> date:
        """Return today's date."""
        return date.today()
