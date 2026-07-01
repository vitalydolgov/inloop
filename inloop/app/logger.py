"""Port for recording everything that happens while the agent runs."""

from dataclasses import dataclass
from typing import Protocol

from inloop.domain import message
from inloop.domain import streaming


@dataclass(frozen=True)
class UserMessage:
    """Text the user sent to the agent."""

    text: str


@dataclass(frozen=True)
class ToolResult:
    """The outcome of running a tool the model requested."""

    call: message.ToolCall
    content: str


Entry = UserMessage | streaming.Event | ToolResult


class Logger(Protocol):
    """Records entries produced while the agent runs."""

    def log(self, entry: Entry) -> None:
        """Record one entry."""
        ...
