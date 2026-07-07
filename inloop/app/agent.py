"""Workflow that drives a chat loop over a stream of user messages."""

import asyncio
from collections.abc import AsyncIterator, Sequence

from inloop.app import compaction
from inloop.app import environment
from inloop.app.conversation import Conversation
from inloop.app.inbox import Inbox
from inloop.app import logger
from inloop.app.logger import logged, logged_stream
from inloop.domain import message
from inloop.domain.message import Message, Role
from inloop.domain import model
from inloop.domain import streaming
from inloop.domain import extension
from inloop.domain import tool

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
        environment: environment.Environment | None = None,
        agent_id: str = "main",
        can_spawn: bool = True,
    ):
        self._model = model
        self._subagent_model = subagent_model or model
        self._environment = environment
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

        if model.context_window > 0:
            self._compactor = compaction.Compactor(model)
        else:
            self._compactor = None

        self.conversation = Conversation()
        """The conversation transcript owned by this agent."""
        self.conversation.add = logged(self._log)(self.conversation.add)
        self._agent_turn = logged_stream(self._log)(self._agent_turn)

    async def events(
        self, messages: AsyncIterator[str]
    ) -> AsyncIterator[streaming.Event]:
        """Ask the model for each message, injecting any typed mid-run as steering."""
        async with Inbox(messages) as inbox:
            async for text in inbox:
                await self.conversation.add(Message(Role.USER, [message.Text(text)]))
                self._interrupted = False
                while True:
                    stop = {}
                    async for event in self._agent_turn(stop):
                        yield event
                    if stop:
                        break
                    for steer in inbox.drain():
                        await self.conversation.add(Message(Role.USER, [message.Text(steer)]))

    def interrupt(self):
        """Ask the current reply to stop streaming as soon as possible, cascading to subagents."""
        self._interrupted = True
        for child in self._children:
            child.interrupt()

    def _system_prompt(self):
        if self._environment is None:
            return ""
        return self._environment.describe()

    async def _log(self, entry):
        if self._logger:
            await self._logger.log(entry, self._id)

    async def _compact_if_needed(self, input_tokens):
        if self._compactor is None or not self._compactor.is_full(input_tokens):
            return
        if not self._compactor.can_compact(self.conversation.history):
            return
        yield streaming.Compaction.STARTED
        self.conversation.history = await self._compactor.compact(self.conversation.history)
        yield streaming.Compaction.ENDED

    async def _spawn(self, args):
        self._child_count += 1
        child = Agent(
            self._subagent_model,
            extensions=self._extensions,
            logger=self._logger,
            environment=self._environment,
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
        input_tokens = 0

        tools = list(self._tools.values())
        stream = self._model.stream(
            self.conversation.history, tools, system=self._system_prompt()
        )
        try:
            async for event in stream:
                match event:
                    case streaming.TextDelta(text):
                        partial += text
                    case streaming.ToolUse(id=id, name=name, input=input):
                        calls.append(message.ToolCall(id, name, input))
                    case streaming.MessageCompleted(text=text):
                        if text:
                            texts.append(message.Text(text))
                        input_tokens = event.input_tokens
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
            await self.conversation.add(Message(Role.ASSISTANT, [message.Text(text)]))
            yield streaming.Interrupted()
            stop["interrupted"] = True
            return

        async def execute(call):
            tool = self._tools[call.name]
            content = await tool.execute(call.input)
            return message.ToolResult(call.id, content)

        try:
            results = await asyncio.gather(*(execute(call) for call in calls))
        except Exception as error:
            yield streaming.Failed(str(error))
            stop["failed"] = True
            return

        assistant_blocks = [*texts, *calls]
        if assistant_blocks:
            await self.conversation.add(Message(Role.ASSISTANT, assistant_blocks))

        if results:
            await self.conversation.add(Message(Role.USER, results))
        else:
            stop["done"] = True

        results_tokens = sum(len(result.content) for result in results) // 4  # roughly
        async for event in self._compact_if_needed(input_tokens + results_tokens):
            yield event
