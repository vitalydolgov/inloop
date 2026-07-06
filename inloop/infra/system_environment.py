"""Environment assembled from the host system."""

from inloop.app import clock


class SystemEnvironment:
    """An Environment describing the host the agent runs on."""

    def __init__(self, clock: clock.Clock) -> None:
        self._clock = clock

    def describe(self) -> str:
        """Return a description of the current environment."""
        parts = [f"Today's date is {self._clock.today().isoformat()}."]
        return "\n".join(parts)
