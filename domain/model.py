"""Port for a language model that streams its response."""

from collections.abc import Iterator, Sequence
from typing import Protocol

from domain import message
from domain import streaming


class Model(Protocol):
    """A language model that answers a conversation as a stream of events."""

    def stream(self, messages: Sequence[message.Message]) -> Iterator[streaming.Event]:
        """Yield response events for the conversation so far."""
        ...
