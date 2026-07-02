"""Events emitted while a model response streams back."""

from dataclasses import dataclass
from enum import Enum


class ThinkingPhase(Enum):
    """A boundary marker for the model's internal reasoning phase."""

    STARTED = "started"
    ENDED = "ended"


@dataclass(frozen=True)
class ThinkingDelta:
    """A chunk of the model's internal reasoning."""

    text: str


class TextPhase(Enum):
    """A boundary marker for the model's visible text phase."""

    STARTED = "started"
    ENDED = "ended"


@dataclass(frozen=True)
class TextDelta:
    """A chunk of generated text."""

    text: str


@dataclass(frozen=True)
class ToolUse:
    """A request from the model to invoke a tool with the given input."""

    id: str
    name: str
    input: dict[str, object]


@dataclass(frozen=True)
class MessageCompleted:
    """The successful end of a streamed response."""

    text: str
    stop_reason: str | None


@dataclass(frozen=True)
class Interrupted:
    """The response was stopped at the user's request before completing."""


@dataclass(frozen=True)
class Failed:
    """The response ended because an unexpected error occurred."""

    error: str


Event = (
    ThinkingPhase
    | ThinkingDelta
    | TextPhase
    | TextDelta
    | ToolUse
    | MessageCompleted
    | Interrupted
    | Failed
)
