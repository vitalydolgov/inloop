"""Run an interactive chat, rendering each reply as the app layer streams it."""

import asyncio
import sys
from collections.abc import AsyncIterator

from app.agent import Agent
from domain import streaming
from infra import extensions

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
    at_bol = True

    def write(text: str) -> None:
        nonlocal at_bol
        print(text, end="", flush=True)
        at_bol = text.endswith("\n")

    def ensure_bol() -> None:
        nonlocal at_bol
        if not at_bol:
            print(flush=True)
            at_bol = True

    async for event in events:
        match event:
            case streaming.ThinkingPhase.STARTED:
                ensure_bol()
                write("[think...]\n")
            case streaming.ThinkingDelta(text):
                write(text)
            case streaming.ThinkingPhase.ENDED:
                ensure_bol()
                write("[...think]\n")
            case streaming.TextDelta(delta):
                write(delta)
            case streaming.ToolUse(_, name, tool_input):
                ensure_bol()
                write(f"[tool: {name} {tool_input}]\n")
            case streaming.MessageCompleted(_, stop_reason):
                ensure_bol()
                write(f"[done: {stop_reason}]\n")


def main():
    """Start the interactive chat demo."""
    import anthropic
    from infra import anthropic_model

    model = anthropic_model.AnthropicModel(
        anthropic.Anthropic(),
        model="claude-sonnet-4-6",
        max_tokens=64_000,
        effort="high"
    )
    agent = Agent(model, extensions=extensions.load())
    events = agent.events(user_input())
    asyncio.run(render(events))