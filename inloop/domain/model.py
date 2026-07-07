"""Port for a language model that streams its response."""

from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from inloop.domain import message
from inloop.domain import streaming
from inloop.domain import tool


class Model(Protocol):
    """A language model that answers a conversation as a stream of events."""

    @property
    def identifier(self) -> str:
        """The model's identifier, such as its provider slug."""
        ...

    @property
    def context_window(self) -> int:
        """The most tokens the model accepts in one request, or 0 when unbounded."""
        ...

    def stream(
        self,
        messages: Sequence[message.Message],
        tools: Sequence[tool.Tool] = (),
        system: str = "",
    ) -> AsyncIterator[streaming.Event]:
        """Yield response events for the conversation, offering the given tools."""
        ...
