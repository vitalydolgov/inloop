"""Run an interactive chat, rendering each reply as the app layer streams it."""

import asyncio
import json
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import rich.box
import rich.console
from rich.panel import Panel
from rich.text import Text

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout

from inloop.app.agent import Agent
from inloop.domain import streaming

from inloop.infra.env_config import EnvConfig
from inloop.infra.directory_registry import DirectoryExtensionRegistry
from inloop.infra.plain_logger import PlainLogger

console = rich.console.Console()


async def piped_lines() -> AsyncIterator[str]:
    """Yield stripped, non-empty lines from non-interactive stdin."""
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        text = line.strip()
        if text:
            yield text


async def prompt_lines(session: PromptSession) -> AsyncIterator[str]:
    """Yield user messages from a prompt that stays available while replies stream."""
    while True:
        try:
            line = await session.prompt_async("› ")
        except EOFError:
            break
        text = line.strip()
        if text:
            yield text


async def render(events: AsyncIterator[streaming.Event]) -> None:
    """Present reply events as the app layer streams them, above a persistent prompt."""
    buffer = ""

    def handle(event: streaming.Event) -> None:
        nonlocal buffer
        match event:
            case streaming.ThinkingPhase.STARTED:
                console.print(Text("Thinking…", style="italic dim"))

            case streaming.ThinkingDelta(_):
                pass

            case streaming.ThinkingPhase.ENDED:
                pass

            case streaming.TextPhase.STARTED:
                buffer = ""

            case streaming.TextDelta(delta):
                buffer += delta
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    console.print(line, markup=False, highlight=False)

            case streaming.TextPhase.ENDED:
                if buffer:
                    console.print(buffer, markup=False, highlight=False)
                    buffer = ""
                console.print()

            case streaming.ToolUse(_, name, tool_input):
                console.print(f"[dim cyan]⛭ {name} {json.dumps(tool_input)}[/dim cyan]")

            case streaming.MessageCompleted(_, _):
                pass

            case streaming.Interrupted():
                console.print("[red]⨯ interrupted[/red]")

            case streaming.Failed(error):
                console.print(f"[red]⨯ error: {error}[/red]")

    async for event in events:
        handle(event)


async def chat(agent: Agent) -> None:
    """Drive the interactive chat, keeping the input prompt available while replies stream."""
    if not sys.stdin.isatty():
        await render(agent.events(piped_lines()))
        return

    console.print(Panel(
        "[bold]→ [blue]Ctrl+C[/blue] to interrupt · [blue]Ctrl+D[/blue] to exit[/bold]",
        border_style="dim",
        box=rich.box.ROUNDED,
        padding=(0, 1),
    ))

    bindings = KeyBindings()

    @bindings.add("c-c")
    def _(event):
        agent.interrupt()

    session: PromptSession = PromptSession(key_bindings=bindings)
    with patch_stdout():
        await render(agent.events(prompt_lines(session)))


def main():
    """Start the interactive chat demo."""
    import anthropic
    from inloop.infra import providers

    client = anthropic.AsyncAnthropic()
    config = EnvConfig()
    registry = DirectoryExtensionRegistry(config.extensions_path())
    agent = Agent(
        model=providers.anthropic.AnthropicModel(
            client,
            model="claude-sonnet-5",
            max_tokens=64_000,
            effort="medium",
        ),
        subagent_model=providers.anthropic.AnthropicModel(
            client,
            model="claude-sonnet-5",
            max_tokens=64_000,
            effort="low",
        ),
        extensions=registry.load(),
        logger=PlainLogger(Path("var/log"))
    )
    asyncio.run(chat(agent))
