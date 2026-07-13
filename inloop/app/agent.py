"""Chat agent that owns a conversation and coordinates model turns and tool execution."""

from collections.abc import AsyncIterator

from inloop.app import command
from inloop.app import compaction
from inloop.app import environment
from inloop.app.conversation import Conversation
from inloop.app.interaction import Interaction
from inloop.app.server_tools import ServerTools
from inloop.app.spawn import Spawner
from inloop.app.turn_source import TurnSource
from inloop.domain import model
from inloop.domain import streaming
from inloop.domain import extension


class Agent:
    """A chat agent that owns its conversation, runs tools, and streams events."""

    def __init__(
        self,
        model: model.Model,
        subagent_model: model.Model | None = None,
        extensions: list[extension.Extension] = [],
        server_tools: ServerTools | None = None,
        commands: list[command.Command] = [],
        environment: environment.Environment | None = None,
        can_spawn: bool = True,
    ):
        self._model = model
        self._commands = commands
        self._system_prompt = environment.describe() if environment else ""
        self._interaction: Interaction | None = None
        self._spawner: Spawner | None = None

        self.conversation = Conversation()
        """The conversation transcript owned by this agent."""

        if can_spawn:
            child_model = subagent_model or model

            def make_child():
                return Agent(
                    child_model,
                    extensions=extensions,
                    server_tools=server_tools,
                    environment=environment,
                    can_spawn=False,
                )

            self._spawner = Spawner(make_child)

        self._source = TurnSource(
            model,
            extensions=extensions,
            server_tools=server_tools,
            spawner=self._spawner,
        )

    @property
    def commands(self) -> list[command.Command]:
        """The commands the user can run in this conversation."""
        return self._commands

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
            commands=self._commands,
            system_prompt=self._system_prompt,
        ) as self._interaction:
            async for event in self._interaction(self.conversation):
                yield event
