"""Integration tests that talk to the real Anthropic Messages API."""

import asyncio
from collections.abc import AsyncIterator, Iterable

import pytest

from inloop.app import agent
from inloop.domain import streaming

pytest.importorskip("anthropic")

from inloop.infra.providers import anthropic

MODEL = "claude-haiku-4-5"

pytestmark = pytest.mark.anthropic


async def _stream(items: list[str]) -> AsyncIterator[str]:
    for item in items:
        yield item


def _run(chat: agent.Agent, messages: list[str]) -> list[streaming.Event]:
    async def gather() -> list[streaming.Event]:
        return [event async for event in chat.events(_stream(messages))]

    return asyncio.run(gather())


def _final_text(events: Iterable[streaming.Event]) -> str:
    text = ""
    for event in events:
        if isinstance(event, streaming.MessageCompleted) and event.text:
            text = event.text
    return text


def _agent() -> agent.Agent:
    client = anthropic.AsyncAnthropic()
    model = anthropic.AnthropicModel(client, model=MODEL, max_tokens=1024, context_window=0)
    return agent.Agent(model)


def test_answers_a_factual_question() -> None:
    chat = _agent()
    events = _run(chat, ["What is the capital of France? Answer in one word."])
    assert "paris" in _final_text(events).lower()


def test_remembers_word_across_messages() -> None:
    chat = _agent()
    secret = "banana"

    events = _run(
        chat,
        [
            f'Remember this word: "{secret}". Just acknowledge briefly.',
            "What was the word I asked you to remember? Reply with only that word.",
        ],
    )

    assert secret in _final_text(events).lower()
