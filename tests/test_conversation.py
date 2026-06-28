"""Tests for the multi-turn conversation workflow."""

from collections.abc import Iterator, Sequence

from app import conversation
from domain import message
from domain import streaming


class _ScriptedModel:
    """A Model that replies with a fixed line per turn and records what it saw."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = iter(replies)
        self.seen: list[list[message.Message]] = []

    def stream(self, messages: Sequence[message.Message]) -> Iterator[streaming.StreamEvent]:
        self.seen.append(list(messages))
        reply = next(self._replies)
        yield streaming.TextDelta(reply)
        yield streaming.MessageCompleted(text=reply, stop_reason="end_turn")


def test_ask_streams_events_for_a_single_turn() -> None:
    model = _ScriptedModel(["hello there"])
    chat = conversation.Conversation(model)

    result = list(chat.ask("hi"))

    assert result == [
        streaming.TextDelta("hello there"),
        streaming.MessageCompleted(text="hello there", stop_reason="end_turn"),
    ]


def test_second_message_includes_prior_turns() -> None:
    model = _ScriptedModel(["first reply", "second reply"])
    chat = conversation.Conversation(model)

    list(chat.ask("first question"))
    list(chat.ask("second question"))

    assert model.seen[0] == [
        message.Message(message.Role.USER, "first question"),
    ]
    assert model.seen[1] == [
        message.Message(message.Role.USER, "first question"),
        message.Message(message.Role.ASSISTANT, "first reply"),
        message.Message(message.Role.USER, "second question"),
    ]
