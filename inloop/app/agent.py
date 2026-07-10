"""Chat agent that owns a conversation and coordinates model turns and tool execution."""

from collections.abc import AsyncIterator, Sequence

from inloop.app import compaction
from inloop.app import environment
from inloop.app.conversation import Conversation
from inloop.app import logger
from inloop.app.interaction import Interaction
from inloop.app.spawn import Spawner, TOOL_NAME as SPAWN_TOOL
from inloop.domain import message
from inloop.domain.message import Message, Role
from inloop.domain import model
from inloop.domain import streaming
from inloop.domain import extension
from inloop.domain import tool


class Agent:
    """A chat agent that owns its conversation, runs tools, and streams events."""

    def __init__(
        self,
        model: model.Model,
        subagent_model: model.Model | None = None,
        extensions: Sequence[extension.Extension] = (),
        logger: logger.Logger | None = None,
        environment: environment.Environment | None = None,
        agent_id: str = "main",
        can_spawn: bool = True,
    ):
        self._model = model
        self._subagent_model = subagent_model or model
        self._environment = environment
        self._extensions = list(extensions)
        self._logger = logger
        self._id = agent_id
        self._interaction: Interaction | None = None

        tools: dict[str, tool.Tool] = {}
        for ext in extensions:
            tools.update(ext.tools_by_name())
        self._spawner = Spawner(self._make_child) if can_spawn else None
        if self._spawner:
            tools[SPAWN_TOOL] = self._spawner.tool()
        self._tools = tools

        self.conversation = Conversation()
        """The conversation transcript owned by this agent."""

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
            tools=self._tools,
            compactor=compaction.Compactor(self._model) if self._model.context_window > 0 else None,
            make_stream=self._make_model_stream,
        ) as self._interaction:
            async for event in self._interaction(self.conversation):
                yield event

    def _make_model_stream(self):
        system = self._environment.describe() if self._environment else ""
        return self._model.stream(
            self.conversation.history,
            list(self._tools.values()),
            system=system,
        )

    def _make_child(self, agent_id):
        return Agent(
            self._subagent_model,
            extensions=self._extensions,
            logger=self._logger,
            environment=self._environment,
            agent_id=agent_id,
            can_spawn=False,
        )
