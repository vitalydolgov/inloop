"""Tests for the conversation transcript."""

from app import conversation
from domain import message


def test_history_starts_empty() -> None:
    convo = conversation.Conversation()

    assert convo.history == []


def test_add_records_messages_in_order() -> None:
    convo = conversation.Conversation()

    hello = message.Message(message.Role.USER, [message.Text("hello")])
    hi_there = message.Message(message.Role.ASSISTANT, [message.Text("hi there")])
    convo.add(hello)
    convo.add(hi_there)

    assert convo.history == [hello, hi_there]
