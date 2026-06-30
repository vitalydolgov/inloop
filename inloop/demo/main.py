"""Run an interactive chat, rendering each reply as the app layer streams it."""

import asyncio
import json
import readline  # noqa: F401
import sys
from collections.abc import AsyncIterator

import rich.console
import rich.live
from rich.markdown import Markdown
from rich.box import Box
from rich.panel import Panel
from rich.text import Text

from inloop.app.agent import Agent
from inloop.domain import streaming
from inloop.infra import extensions

console = rich.console.Console()


async def stdin_lines() -> AsyncIterator[str]:
    """Yield lines from stdin without blocking the event loop."""
    loop = asyncio.get_running_loop()
    interactive = sys.stdin.isatty()
    prompt = "\001\033[2m\002› \001\033[0m\002" if interactive else ""
    while True:
        try:
            line = await loop.run_in_executor(None, input, prompt)
        except EOFError:
            if interactive:
                console.print()
            break

        if not interactive:
            yield line
            continue

        sys.stdout.write("\033[1A\033[2K")
        sys.stdout.flush()
        if line.strip():
            console.print(Panel(
                line.strip(),
                border_style="blue",
                box=rich.box.ROUNDED,
                padding=(0, 1),
            ))
        yield line


async def user_input() -> AsyncIterator[str]:
    """Yield meaningful user messages for the chat."""
    async for line in stdin_lines():
        text = line.strip()
        if text:
            yield text


async def render(events: AsyncIterator[streaming.Event]) -> None:
    """Present reply events as the app layer streams them."""
    live = rich.live.Live(console=console, refresh_per_second=20)
    text_buffer = ""

    async for event in events:
        match event:
            case streaming.ThinkingPhase.STARTED:
                pass

            case streaming.ThinkingDelta(text):
                console.print(Text(text, style="italic dim"), end="")

            case streaming.ThinkingPhase.ENDED:
                console.print()
                console.print()

            case streaming.TextDelta(delta):
                if not live.is_started:
                    text_buffer = ""
                    live.start()
                text_buffer += delta
                live.update(Markdown(text_buffer))

            case streaming.ToolUse(_, name, tool_input):
                live.stop()
                console.print(f"[dim cyan]{name}[/dim cyan] {json.dumps(tool_input)}")

            case streaming.MessageCompleted(_, stop_reason):
                live.stop()
                if stop_reason and stop_reason not in ("end_turn", "tool_use"):
                    console.print(f"[dim]({stop_reason})[/dim]")
                console.print()


def main():
    """Start the interactive chat demo."""
    import anthropic
    from inloop.infra import providers

    model = providers.anthropic.AnthropicModel(
        anthropic.Anthropic(),
        model="claude-sonnet-5",
        max_tokens=64_000,
        effort="low"
    )
    agent = Agent(model, extensions=extensions.load())
    events = agent.events(user_input())
    asyncio.run(render(events))