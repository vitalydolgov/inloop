"""A single message in a conversation."""

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    """The author of a message."""

    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class Message:
    """One turn of a conversation, authored by a user or the assistant."""

    role: Role
    content: str
