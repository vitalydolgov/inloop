"""A single message in a conversation."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable


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


@runtime_checkable
class ToolResult(Protocol):
    """Outcome of a tool the assistant requested."""

    tool_call_id: str
    content: str


@dataclass(frozen=True)
class ToolSuccess:
    """A successful tool outcome."""

    tool_call_id: str
    content: str


@dataclass(frozen=True)
class ToolFailure:
    """A failed tool outcome."""

    tool_call_id: str
    content: str


Block = Text | ToolCall | ToolResult


@dataclass(frozen=True)
class Message:
    """One turn of a conversation, authored by a user or the assistant."""

    role: Role
    content: list[Block]
