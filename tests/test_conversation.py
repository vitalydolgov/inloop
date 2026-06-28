"""Tests for the conversation transcript."""

from app import conversation
from domain import message


def test_history_starts_empty() -> None:
    convo = conversation.Conversation()

    assert convo.history == []


def test_add_records_messages_in_order() -> None:
    convo = conversation.Conversation()

    convo.add(message.Role.USER, "hello")
    convo.add(message.Role.ASSISTANT, "hi there")

    assert convo.history == [
        message.Message(message.Role.USER, "hello"),
        message.Message(message.Role.ASSISTANT, "hi there"),
    ]
