"""Tests for the single-request workflow."""

from collections.abc import Iterator

from app import conversation
from domain import streaming


class _StubModel:
    """A Model that replays a fixed list of events."""

    def __init__(self, events: list[streaming.StreamEvent]) -> None:
        self._events = events
        self.asked_with: str | None = None

    def stream(self, message: str) -> Iterator[streaming.StreamEvent]:
        self.asked_with = message
        yield from self._events


def test_ask_streams_model_events_for_the_message() -> None:
    events = [
        streaming.TextDelta("hi"),
        streaming.MessageCompleted(text="hi", stop_reason="end_turn"),
    ]
    model = _StubModel(events)

    result = list(conversation.ask(model, "question"))

    assert result == events
    assert model.asked_with == "question"
