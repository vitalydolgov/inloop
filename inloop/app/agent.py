"""Chat agent that owns a conversation and coordinates model turns and tool execution."""

from collections.abc import AsyncIterator

from inloop.app import compaction
from inloop.app import reload
from inloop.app.conversation import Conversation
from inloop.app.interaction import Interaction
from inloop.app.server_tools import ServerTools
from inloop.app.spawn import Spawner
from inloop.app.turn_source import TurnSource
from inloop.domain import model
from inloop.domain import streaming
from inloop.domain import extension
from inloop.domain import tool


class Agent:
    """A chat agent that owns its conversation, runs tools, and streams events."""

    def __init__(
        self,
        model: model.Model,
        *,
        subagent_model: model.Model | None = None,
        extensions: list[extension.Extension] | None = None,
        server_tools: ServerTools | None = None,
        system_prompt: str = "",
        tools: list[tool.Tool] | None = None,
        _spawn: bool = True,
    ):
        self._model = model
        self._extensions = list(extensions or [])
        self._builtin_tools = list(tools or [])
        self._server_tools = server_tools
        self._system_prompt = system_prompt
        self._interaction: Interaction | None = None
        self._spawner: Spawner | None = None

        self.conversation = Conversation()
        """The conversation transcript owned by this agent."""

        extra_tools = list(self._builtin_tools)
        if _spawn:
            subagent_model = subagent_model or model
            self._spawner = Spawner(lambda: self._make_child(subagent_model))
            extra_tools.append(self._spawner.tool())
        if self._server_tools is not None:
            extra_tools.append(reload.make_tool(self._server_tools))

        self._source = TurnSource(
            model,
            extensions=self._extensions,
            server_tools=self._server_tools,
            extra_tools=extra_tools,
        )

    def _make_child(self, model):
        return Agent(
            model,
            extensions=self._extensions,
            server_tools=self._server_tools,
            system_prompt=self._system_prompt,
            tools=self._builtin_tools,
            _spawn=False,
        )

    def interrupt(self):
        """Ask the current response to stop as soon as possible, cascading to subagents."""
        if self._spawner:
            for child in list(self._spawner.children):
                child.interrupt()
        if self._interaction is not None:
            self._interaction.interrupt()

    async def events(
        self, messages: AsyncIterator[str]
    ) -> AsyncIterator[streaming.Event]:
        """Run an interaction over the given messages and yield agent events."""
        async with Interaction(
            messages,
            compactor=compaction.Compactor(self._model) if self._model.context_window > 0 else None,
            source=self._source,
            system_prompt=self._system_prompt,
        ) as self._interaction:
            async for event in self._interaction(self.conversation):
                yield event
