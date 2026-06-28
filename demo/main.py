"""Run an interactive chat, rendering each reply as the app layer streams it."""

import asyncio
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import anthropic

from app.agent import Agent
from domain import streaming
from infra import anthropic_model
from infra import extensions

MANIFEST = Path(__file__).resolve().parent.parent / "extensions.toml"


async def stdin_lines() -> AsyncIterator[str]:
    """Yield lines from stdin without blocking the event loop."""
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), sys.stdin)
    interactive = sys.stdin.isatty()
    while True:
        if interactive:
            print("> ", end="", flush=True)
        line = await reader.readline()
        if not line:
            break
        yield line.decode()


async def user_input() -> AsyncIterator[str]:
    """Yield meaningful user messages for the chat."""
    async for line in stdin_lines():
        text = line.strip()
        if text:
            yield text


async def render(events: AsyncIterator[streaming.Event]) -> None:
    """Present reply events as the app layer streams them."""
    async for event in events:
        match event:
            case streaming.TextDelta(delta):
                print(delta, end="", flush=True)
            case streaming.ToolUse(_, name, tool_input):
                print(f"\n[tool: {name.replace('__', ':', 1)} {tool_input}]")
            case streaming.MessageCompleted(_, stop_reason):
                print(f"\n[done: {stop_reason}]")


def main():
    """Start the interactive Anthropic-backed chat demo."""
    model = anthropic_model.AnthropicModel(anthropic.Anthropic())
    agent = Agent(model, extensions=extensions.load(MANIFEST))
    events = agent.events(user_input())
    asyncio.run(render(events))