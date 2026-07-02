"""Run an interactive chat, rendering each reply as the app layer streams it."""

import asyncio
import json
import readline  # noqa: F401
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import rich.console
import rich.live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from inloop.app.agent import Agent
from inloop.domain import streaming

from inloop.infra.env_config import EnvConfig
from inloop.infra.directory_registry import DirectoryExtensionRegistry
from inloop.infra.plain_logger import PlainLogger

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
    at_bol = True
    at_blank_line = True

    def separate() -> None:
        nonlocal at_bol, at_blank_line
        if not at_bol:
            console.print()
        if not at_blank_line:
            console.print()
        at_bol = True
        at_blank_line = True

    async for event in events:
        match event:
            case streaming.ThinkingPhase.STARTED:
                pass

            case streaming.ThinkingDelta(text):
                console.print(Text(text, style="italic dim"), end="")
                if text:
                    at_bol = text.endswith("\n")
                    at_blank_line = False

            case streaming.ThinkingPhase.ENDED:
                separate()

            case streaming.TextPhase.STARTED:
                text_buffer = ""
                live.start()

            case streaming.TextDelta(delta):
                text_buffer += delta
                live.update(Markdown(text_buffer))

            case streaming.TextPhase.ENDED:
                live.stop()
                at_bol = True
                at_blank_line = not text_buffer
                separate()

            case streaming.ToolUse(_, name, tool_input):
                live.stop()
                console.print(f"[dim cyan]⛭ {name} {json.dumps(tool_input)}[/dim cyan]")
                at_bol = True
                at_blank_line = False

            case streaming.MessageCompleted(_, stop_reason):
                live.stop()
                separate()


def main():
    """Start the interactive chat demo."""
    import anthropic
    from inloop.infra import providers

    model = providers.anthropic.AnthropicModel(
        anthropic.AsyncAnthropic(),
        model="claude-sonnet-5",
        max_tokens=64_000,
        effort="low"
    )
    config = EnvConfig()
    registry = DirectoryExtensionRegistry(config.extensions_path())
    logger = PlainLogger(Path("var/log"))
    agent = Agent(model, extensions=registry.load(), logger=logger)
    events = agent.events(user_input())
    asyncio.run(render(events))