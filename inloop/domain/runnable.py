"""Port for something that runs a message stream and yields agent events."""

from collections.abc import AsyncIterator
from typing import Protocol

from inloop.domain import streaming


class Runnable(Protocol):
    """Turns a stream of user messages into a stream of agent events."""

    def events(self, messages: AsyncIterator[str]) -> AsyncIterator[streaming.Event]:
        """Run against the given messages and yield events."""
        ...

    def interrupt(self):
        """Ask the current response to stop as soon as possible."""
        ...
