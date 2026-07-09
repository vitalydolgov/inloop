"""Chat agent that owns a conversation and coordinates model turns and tool execution."""

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


class _TurnExecutor:
    """Coordinates one agent turn (model streaming, tool execution, and compaction)."""

    def __init__(
        self,
        model: model.Model,
        tools: dict[str, tool.Tool],
        compactor: compaction.Compactor | None,
    ):
        self._model = model
        self._tools = tools
        self._compactor = compactor
        self._stop: dict[str, bool] = {}

    async def _execute(self, call):
        tool = self._tools[call.name]
        try:
            content = await tool.execute(call.input)
            return message.ToolSuccess(call.id, content)
        except Exception as error:
            return message.ToolFailure(call.id, f"error: {error}")

    async def _compact_if_needed(self, input_tokens, conversation: Conversation):
        if self._compactor is None or not self._compactor.is_full(input_tokens):
            return
        if not self._compactor.can_compact(conversation.history):
            return
        yield streaming.Compaction.STARTED
        conversation.history = await self._compactor.compact(conversation.history)
        yield streaming.Compaction.ENDED

    async def events(self, conversation: Conversation, system_prompt: str):
        self._stop = {}
        stop = self._stop
        calls = []
        texts = []
        partial = ""
        input_tokens = 0

        stream = self._model.stream(
            conversation.history,
            list(self._tools.values()),
            system=system_prompt,
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
        except Exception as error:
            yield streaming.Failed(str(error))
            stop["failed"] = True
            return

        results = await asyncio.gather(*(self._execute(call) for call in calls))

        assistant_blocks = [*texts, *calls]
        if assistant_blocks:
            await conversation.add(Message(Role.ASSISTANT, assistant_blocks))

        if results:
            await conversation.add(Message(Role.USER, results))
        else:
            stop["done"] = True

        results_tokens = sum(len(r.content) for r in results) // 4  # roughly
        async for event in self._compact_if_needed(input_tokens + results_tokens, conversation):
            yield event

    @property
    def should_stop(self) -> bool:
        return bool(self._stop)


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
        tools = {}
        for ext in extensions:
            tools.update(ext.tools_by_name())
        if can_spawn:
            tools[SUBAGENT_TOOL] = tool.Tool(
                SUBAGENT_TOOL, SUBAGENT_DESCRIPTION, SUBAGENT_PARAMETERS, self._spawn
            )
        self._logger = logger
        self._id = agent_id
        self._children = []
        self._child_count = 0

        compactor = compaction.Compactor(model) if model.context_window > 0 else None
        self._turn_executor = _TurnExecutor(model=model, tools=tools, compactor=compactor)
        self._turn_executor.events = logged_stream(self._log)(self._turn_executor.events)

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
                    async for event in self._turn_executor.events(
                        self.conversation, self._system_prompt()
                    ):
                        yield event
                    if self._turn_executor.should_stop:
                        break
                    for steer in inbox.drain():
                        await self.conversation.add(Message(Role.USER, [message.Text(steer)]))

    def _system_prompt(self):
        if self._environment is None:
            return ""
        return self._environment.describe()

    async def _log(self, entry):
        if self._logger:
            await self._logger.log(entry, self._id)

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

            async def _once(text):
                yield text

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