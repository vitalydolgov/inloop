"""Tests for the host-assembled environment description."""

from datetime import date

from inloop.infra.system_environment import SystemEnvironment


class _FixedClock:
    """A Clock stuck at a given date."""

    def __init__(self, today: date) -> None:
        self._today = today

    def today(self) -> date:
        return self._today


def test_describes_todays_date() -> None:
    environment = SystemEnvironment(_FixedClock(date(2026, 7, 6)))

    assert environment.describe() == "Today's date is 2026-07-06."
