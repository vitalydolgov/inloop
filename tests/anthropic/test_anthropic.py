"""Integration tests that talk to the real Anthropic Messages API."""

import asyncio
from collections.abc import AsyncIterator, Iterable

import anthropic
import pytest

from app import agent
from demo.tools import calculator
from domain import streaming
from domain import tool
from infra import anthropic_model

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


def _agent(tools: list[tool.Tool] = []) -> agent.Agent:
    client = anthropic.Anthropic()
    return agent.Agent(anthropic_model.AnthropicModel(client, model=MODEL), tools=tools)


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


def test_runs_the_calculator_tool() -> None:
    chat = _agent(tools=[calculator.calculator])
    events = _run(chat, ["What is 2 + 2 * 3? Use the calculator tool."])

    tool_uses = [e for e in events if isinstance(e, streaming.ToolUse)]
    assert any(use.name == "calculator" for use in tool_uses)
    assert "8" in _final_text(events)
