"""Integration tests that talk to the real Anthropic Messages API."""

import os
from collections.abc import Iterable

import anthropic
import pytest

from app import conversation
from domain import streaming
from infra import anthropic_model

MODEL = "claude-haiku-4-5"

pytestmark = pytest.mark.anthropic

def _final_text(events: Iterable[streaming.StreamEvent]) -> str:
    text = ""
    for event in events:
        if isinstance(event, streaming.MessageCompleted):
            text = event.text
    return text


def _chat() -> conversation.Conversation:
    client = anthropic.Anthropic()
    return conversation.Conversation(anthropic_model.AnthropicModel(client, model=MODEL))


def test_answers_a_factual_question() -> None:
    chat = _chat()
    reply = _final_text(chat.ask("What is the capital of France? Answer in one word."))
    assert "paris" in reply.lower()


def test_remembers_word_across_messages() -> None:
    chat = _chat()
    secret = "banana"

    _final_text(chat.ask(f'Remember this word: "{secret}". Just acknowledge briefly.'))
    reply = _final_text(
        chat.ask("What was the word I asked you to remember? Reply with only that word.")
    )

    assert secret in reply.lower()
