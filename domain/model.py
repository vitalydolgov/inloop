"""Port for a language model that streams its response."""

from collections.abc import Iterator
from typing import Protocol

from domain import streaming


class Model(Protocol):
    """A language model that answers a single user message as a stream of events."""

    def stream(self, message: str) -> Iterator[streaming.StreamEvent]: ...
