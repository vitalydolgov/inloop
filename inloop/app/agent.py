"""Chat agent that owns a conversation and coordinates model turns and tool execution."""

from collections.abc import AsyncIterator, Sequence

from inloop.app import compaction
from inloop.app import environment
from inloop.app.conversation import Conversation
from inloop.app.inbox import Inbox
from inloop.app import logger
from inloop.app.logger import logged, logged_stream
from inloop.app.spawn import Spawner, TOOL_NAME as SPAWN_TOOL
from inloop.app.turn import Turn, TurnResult
from inloop.domain import message
from inloop.domain.message import Message, Role
from inloop.domain import model
from inloop.domain import streaming
from inloop.domain import extension
from inloop.domain import tool


class Agent:
    """A chat agent that owns its conversation, runs tools, and streams replies."""

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

        tools: dict[str, tool.Tool] = {}
        for ext in extensions:
            tools.update(ext.tools_by_name())
        self._spawner = Spawner(self._make_child) if can_spawn else None
        if self._spawner:
            tools[SPAWN_TOOL] = self._spawner.tool()
        self._tools = tools

        compactor = compaction.Compactor(model) if model.context_window > 0 else None
        self._turn = Turn(tools=tools, compactor=compactor, make_stream=self._make_stream)
        self._turn.events = logged_stream(self._log)(self._turn.events)

        self.conversation = Conversation()
        """The conversation transcript owned by this agent."""
        self.conversation.add = logged(self._log)(self.conversation.add)

    async def events(
        self, messages: AsyncIterator[str]
    ) -> AsyncIterator[streaming.Event]:
        """Ask the model for each message, injecting any typed mid-run as steering."""
        async with Inbox(messages) as inbox:
            async for text in inbox:
                await self.conversation.add(Message(Role.USER, [message.Text(text)]))
                while True:
                    async for event in self._turn.events(self.conversation):
                        yield event
                    if self._turn.result is not TurnResult.CONTINUE:
                        break
                    for steer in inbox.drain():
                        await self.conversation.add(Message(Role.USER, [message.Text(steer)]))

    def _make_stream(self):
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

    async def _log(self, entry):
        if self._logger:
            await self._logger.log(entry, self._id)
