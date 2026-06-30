"""A single message in a conversation."""

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    """The author of a message."""

    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class Text:
    """Plain text content."""

    text: str


@dataclass(frozen=True)
class ToolCall:
    """A tool invocation the assistant requested, with the input it chose."""

    id: str
    name: str
    input: dict[str, object]


@dataclass(frozen=True)
class ToolResult:
    """The outcome of running a previously requested tool."""

    tool_call_id: str
    content: str


Block = Text | ToolCall | ToolResult


@dataclass(frozen=True)
class Message:
    """One turn of a conversation, authored by a user or the assistant."""

    role: Role
    content: list[Block]
