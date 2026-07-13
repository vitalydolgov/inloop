"""Run an interactive chat, rendering each reply as the app layer streams it."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import rich.box
import rich.console
import rich.live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style

from inloop.app.agent import Agent
from inloop.app.command import Command
from inloop.app.server_tools import ServerTools
from inloop.domain import streaming

from inloop.infra import app_dirs
from inloop.infra import providers
from inloop.infra import toml_config
from inloop.infra.directory_registry import DirectoryExtensionRegistry
from inloop.infra.plain_logger import PlainLogger
from inloop.infra.system_clock import SystemClock
from inloop.infra.system_environment import SystemEnvironment


PROMPT = [("class:arrow", "\u203a ")]
PROMPT_STYLE = Style.from_dict({
    "arrow": "dim",
    "status": "italic fg:ansibrightblack",
})


class Renderer:
    """Present reply events in the console, tracking a status label."""

    def __init__(self):
        self.console = rich.console.Console()
        self.status = ""
        self._live = None
        self._text = ""

    def render_banner(self, model_identifier):
        self.console.print(Panel(
            f"[bold]\u2192 [blue]Ctrl+C[/blue] to interrupt \u00b7 [blue]Ctrl+D[/blue] to exit[/bold]\n"
            f"\n"
            f"[dim]\u25aa\ufe0e Model:[/dim] {model_identifier}",
            border_style="dim",
            box=rich.box.ROUNDED,
            padding=(0, 1),
        ))

    def echo_input(self, text):
        self.console.print(Text.assemble(("\u203a ", "dim"), text, style="bold"))
        self.console.print()
        self.status = "\u25cb sending\u2026"

    def render_event(self, event):
        match event:
            case streaming.ThinkingPhase.STARTED:
                self.status = "\u25cb thinking\u2026"

            case streaming.TextPhase.STARTED:
                self.status = "\u25cf responding\u2026"
                self._text = ""
                self._live = rich.live.Live(console=self.console, vertical_overflow="visible")
                self._live.start()

            case streaming.TextDelta(text):
                self._text += text
                if self._live:
                    self._live.update(Markdown(self._text))

            case streaming.TextPhase.ENDED:
                self._end_live()
                self.status = ""
                self.console.print()

            case streaming.ToolUse(_, name, tool_input):
                self._end_live()
                self.status = ""
                name = name.replace('__', ':', 1)
                self.console.print(Text(f"\u26ed {name} {json.dumps(tool_input)}", style="dim cyan"))
                self.console.print()

            case streaming.Compaction.STARTED:
                self._end_live()
                self.status = "\u25cb compacting\u2026"

            case streaming.Compaction.ENDED:
                self._end_live()
                self.status = ""
                self.console.print(Text("\u2723 compacted", style="dim cyan"))
                self.console.print()

            case streaming.CommandCompleted(name):
                self._end_live()
                self.status = ""
                self.console.print(Text(f"\u2723 done", style="dim cyan"))
                self.console.print()

            case streaming.Interrupted():
                self._end_live()
                self.status = ""
                self.console.print(Text("\u2a2f interrupted", style="red"))
                self.console.print()

            case streaming.Failed(error):
                self._end_live()
                self.status = ""
                self.console.print(Text(f"\u2a2f error: {error}", style="red"))
                self.console.print()

    def _end_live(self):
        if self._live:
            self._live.stop()
            self._live = None


class Prompt:
    """Bottom-pinned input line that queues submitted text for the agent."""

    def __init__(self, status, on_submit, on_interrupt):
        self._status = status
        self._on_submit = on_submit
        self._on_interrupt = on_interrupt
        self._queue = asyncio.Queue()
        self._session = PromptSession(
            key_bindings=self._bindings(),
            style=PROMPT_STYLE,
            erase_when_done=True,
        )

    def _bindings(self):
        bindings = KeyBindings()

        @bindings.add("c-c")
        def _(event):
            buffer = event.current_buffer
            if buffer.text:
                buffer.reset()
            else:
                self._on_interrupt()

        return bindings

    def _message(self):
        if label := self._status():
            return [("class:status", label), ("", "\n"), *PROMPT]
        return PROMPT

    async def read_loop(self):
        while True:
            try:
                line = await self._session.prompt_async(
                    self._message,
                    style=PROMPT_STYLE,
                    handle_sigint=False,  # ctrl+c goes to our key binding
                )
            except (EOFError, KeyboardInterrupt):
                await self._queue.put(None)  # sentinel: tell lines() to stop
                return
            if text := line.strip():
                self._on_submit(text)
                await self._queue.put(text)

    async def lines(self):
        while (text := await self._queue.get()) is not None:
            yield text

    def refresh(self):
        if self._session.app.is_running:
            self._session.app.invalidate()


async def _piped_input():
    loop = asyncio.get_running_loop()
    while True:
        try:
            line = await loop.run_in_executor(None, input)
        except EOFError:
            return
        if text := line.strip():
            yield text


async def chat(agent, model_identifier, no_banner=False):
    """Drive the interactive chat, keeping the input pinned to the bottom."""
    renderer = Renderer()
    interactive = sys.stdin.isatty()

    if interactive:
        if not no_banner:
            renderer.render_banner(model_identifier)
        prompt = Prompt(
            status=lambda: renderer.status,
            on_submit=renderer.echo_input,
            on_interrupt=agent.interrupt,
        )
        lines, refresh = prompt.lines(), prompt.refresh
    else:
        lines, refresh = _piped_input(), lambda: None

    with patch_stdout(raw=True):
        task = asyncio.create_task(prompt.read_loop()) if interactive else None
        try:
            async for event in agent.events(lines):
                renderer.render_event(event)
                refresh()
        finally:
            if task:
                task.cancel()


async def amain():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-banner", action="store_true", help="suppress the startup banner"
    )
    args = parser.parse_args()

    config = toml_config.TomlConfig(app_dirs.config_path())
    if mock := os.environ.get("MOCK"):
        model = providers.mock.MockModel(Path(mock), delay=0.01)
        subagent_model = None
    else:
        model = config.agent.model()
        subagent_model = config.subagent.model()

    async with ServerTools(config.mcp) as mcp_tools:
        registry = DirectoryExtensionRegistry(app_dirs.extensions_dir())
        agent = Agent(
            model=model,
            subagent_model=subagent_model,
            extensions=registry.load(),
            server_tools=mcp_tools,
            commands=[
                Command("reload", "reconnect the configured tool servers", mcp_tools.reload),
            ],
            logger=PlainLogger(app_dirs.log_dir()),
            environment=SystemEnvironment(SystemClock()),
        )
        await chat(agent, model.identifier, no_banner=args.no_banner)


def main():
    asyncio.run(amain())