"""Workflow that drives a chat loop over a stream of user messages."""

import asyncio
from collections.abc import AsyncIterator, Sequence

from inloop.app.conversation import Conversation
from inloop.app import logger
from inloop.domain import message
from inloop.domain.message import Message, Role
from inloop.domain import model
from inloop.domain import streaming
from inloop.domain import extension

COMMANDS = frozenset({"/exit", "/quit"})


class Agent:
    """A chat agent that owns its conversation, runs tools, and streams replies."""

    def __init__(
        self,
        language_model: model.Model,
        extensions: Sequence[extension.Extension] = (),
        logger: logger.Logger | None = None,
    ) -> None:
        self._model = language_model
        self._tools = {}
        for ext in extensions:
            self._tools.update(ext.tools_by_name())
        self._logger = logger
        self.conversation = Conversation()
        """The conversation transcript owned by this agent."""

    async def events(
        self, messages: AsyncIterator[str]
    ) -> AsyncIterator[streaming.Event]:
        """Ask the model for each non-command message, running any tools it requests."""
        async for user_text in messages:
            if user_text in COMMANDS:
                return

            self._log(logger.UserMessage(user_text))
            self.conversation.add(Message(Role.USER, [message.Text(user_text)]))

            async for event in self._agent_turn():
                yield event

    def _log(self, entry: logger.Entry) -> None:
        if self._logger:
            self._logger.log(entry)

    async def _agent_turn(self) -> AsyncIterator[streaming.Event]:
        async def execute(call: message.ToolCall) -> message.ToolResult:
            tool = self._tools[call.name]
            content = await tool.execute(call.input)
            self._log(logger.ToolResult(call, content))
            return message.ToolResult(call.id, content)

        while True:
            calls = []
            texts = []

            tools = list(self._tools.values())
            async for event in self._model.stream(self.conversation.history, tools):
                self._log(event)
                match event:
                    case streaming.ToolUse():
                        call = message.ToolCall(event.id, event.name, event.input)
                        calls.append(call)
                    case streaming.MessageCompleted() if event.text:
                        texts.append(message.Text(event.text))
                yield event

            results = await asyncio.gather(*(execute(call) for call in calls))

            assistant_blocks = [*texts, *calls]
            if assistant_blocks:
                self.conversation.add(Message(Role.ASSISTANT, assistant_blocks))

            if results:
                self.conversation.add(Message(Role.USER, results))
            else:
                break
