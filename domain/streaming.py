"""Events emitted while a model response streams back."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TextDelta:
    """A chunk of generated text."""

    text: str


@dataclass(frozen=True)
class MessageCompleted:
    """The successful end of a streamed response."""

    text: str
    stop_reason: str | None


Event = TextDelta | MessageCompleted
