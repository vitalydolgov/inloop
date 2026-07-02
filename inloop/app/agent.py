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
from inloop.domain import tool

COMMANDS = frozenset({"/exit", "/quit"})

INTERRUPTED_NOTICE = "[Interrupted by user]"

SUBAGENT_TOOL = "agent__spawn"

SUBAGENT_DESCRIPTION = (
    "Delegate a scoped task to a fresh subagent and return its final answer. "
    "The subagent runs its own conversation with the same tools and reports back."
)

SUBAGENT_PARAMETERS = {
    "type": "object",
    "properties": {
        "task": {
            "type": "string",
            "description": "The task for the subagent to carry out.",
        }
    },
    "required": ["task"],
}


async def _once(text):
    yield text


class Agent:
    """A chat agent that owns its conversation, runs tools, and streams replies."""

    def __init__(
        self,
        model: model.Model,
        subagent_model: model.Model | None = None,
        extensions: Sequence[extension.Extension] = (),
        logger: logger.Logger | None = None,
        agent_id: str = "main",
        can_spawn: bool = True,
    ):
        self._model = model
        self._subagent_model = subagent_model or model
        self._extensions = list(extensions)
        self._tools = {}
        for ext in extensions:
            self._tools.update(ext.tools_by_name())
        if can_spawn:
            self._tools[SUBAGENT_TOOL] = tool.Tool(
                SUBAGENT_TOOL, SUBAGENT_DESCRIPTION, SUBAGENT_PARAMETERS, self._spawn
            )
        self._logger = logger
        self._id = agent_id
        self._children = []
        self._child_count = 0
        self._interrupted = False
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

            self._interrupted = False
            while True:
                stop = {}
                async for event in self._agent_turn(stop):
                    self._log(event)
                    yield event
                if stop:
                    break

    def interrupt(self):
        """Ask the current reply to stop streaming as soon as possible, cascading to subagents."""
        self._interrupted = True
        for child in self._children:
            child.interrupt()

    def _log(self, entry):
        if self._logger:
            self._logger.log(entry, self._id)

    async def _spawn(self, args):
        self._child_count += 1
        child = Agent(
            self._subagent_model,
            extensions=self._extensions,
            logger=self._logger,
            agent_id=f"sub-{self._child_count}",
            can_spawn=False,
        )
        self._children.append(child)
        try:
            final = ""
            async for event in child.events(_once(args["task"])):
                match event:
                    case streaming.MessageCompleted(text) if text:
                        final = text
                    case streaming.Failed(error):
                        return f"[subagent failed: {error}]"
                    case streaming.Interrupted():
                        return final or INTERRUPTED_NOTICE
            return final
        finally:
            self._children.remove(child)

    async def _agent_turn(self, stop):
        calls = []
        texts = []
        partial = ""

        tools = list(self._tools.values())
        stream = self._model.stream(self.conversation.history, tools)
        try:
            async for event in stream:
                match event:
                    case streaming.TextDelta(text):
                        partial += text
                    case streaming.ToolUse():
                        call = message.ToolCall(event.id, event.name, event.input)
                        calls.append(call)
                    case streaming.MessageCompleted() if event.text:
                        texts.append(message.Text(event.text))
                yield event
                if self._interrupted:
                    await stream.aclose()
                    break
        except Exception as error:
            yield streaming.Failed(str(error))
            stop["failed"] = True
            return

        if self._interrupted:
            text = f"{partial}\n\n{INTERRUPTED_NOTICE}" if partial else INTERRUPTED_NOTICE
            self.conversation.add(Message(Role.ASSISTANT, [message.Text(text)]))
            yield streaming.Interrupted()
            stop["interrupted"] = True
            return

        async def execute(call):
            tool = self._tools[call.name]
            content = await tool.execute(call.input)
            self._log(logger.ToolResult(call, content))
            return message.ToolResult(call.id, content)

        try:
            results = await asyncio.gather(*(execute(call) for call in calls))
        except Exception as error:
            yield streaming.Failed(str(error))
            stop["failed"] = True
            return

        assistant_blocks = [*texts, *calls]
        if assistant_blocks:
            self.conversation.add(Message(Role.ASSISTANT, assistant_blocks))

        if results:
            self.conversation.add(Message(Role.USER, results))
        else:
            stop["done"] = True
