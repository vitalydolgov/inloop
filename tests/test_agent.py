"""Tests for the chat agent workflow."""

import asyncio
from collections.abc import AsyncIterator, Iterator, Sequence

from inloop.app import agent
from inloop.domain import extension
from inloop.domain import message
from inloop.domain import streaming
from inloop.domain import tool


class _ScriptedModel:
    """A Model that replies with a fixed line per turn and records what it saw."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = iter(replies)
        self.seen: list[list[message.Message]] = []
        self.offered_tools: list[list[tool.Tool]] = []

    def stream(
        self,
        messages: Sequence[message.Message],
        tools: Sequence[tool.Tool] = (),
    ) -> Iterator[streaming.Event]:
        self.seen.append(list(messages))
        self.offered_tools.append(list(tools))
        reply = next(self._replies)
        yield streaming.TextDelta(reply)
        yield streaming.MessageCompleted(text=reply, stop_reason="end_turn")


class _TurnModel:
    """A Model that yields a scripted list of events per turn and records history."""

    def __init__(self, turns: list[list[streaming.Event]]) -> None:
        self._turns = iter(turns)
        self.seen: list[list[message.Message]] = []

    def stream(
        self,
        messages: Sequence[message.Message],
        tools: Sequence[tool.Tool] = (),
    ) -> Iterator[streaming.Event]:
        self.seen.append(list(messages))
        yield from next(self._turns)


async def _stream(items: list[str]) -> AsyncIterator[str]:
    for item in items:
        yield item


def _collect(messages: list[str], replies: list[str]) -> list[streaming.Event]:
    chat_agent = agent.Agent(_ScriptedModel(replies))

    async def gather() -> list[streaming.Event]:
        return [event async for event in chat_agent.events(_stream(messages))]

    return asyncio.run(gather())


def test_run_streams_events_for_each_message() -> None:
    events = _collect(["hi", "again"], ["one", "two"])

    assert events == [
        streaming.TextDelta("one"),
        streaming.MessageCompleted(text="one", stop_reason="end_turn"),
        streaming.TextDelta("two"),
        streaming.MessageCompleted(text="two", stop_reason="end_turn"),
    ]


def test_run_stops_on_command() -> None:
    events = _collect(["/exit", "ignored"], ["unused"])

    assert events == []


def test_offers_its_tools_to_the_model() -> None:
    weather = tool.Tool(
        name="weather",
        description="Look up the weather.",
        parameters={"type": "object", "properties": {}},
        execute=lambda args: "sunny",
    )
    model = _ScriptedModel(["sure"])
    chat_agent = agent.Agent(model, extensions=[extension.Extension("test", [weather])])

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["hi"])):
            pass

    asyncio.run(gather())

    namespaced = extension.Extension("test", [weather]).tools_by_name()["test__weather"]
    assert model.offered_tools == [[namespaced]]


def test_runs_requested_tool_and_feeds_result_back() -> None:
    ran: list[dict[str, object]] = []

    def run(args: dict[str, object]) -> str:
        ran.append(args)
        return "4"

    adder = tool.Tool(
        name="add",
        description="Add two numbers.",
        parameters={"type": "object", "properties": {}},
        execute=run,
    )

    class _ToolThenAnswer:
        def __init__(self) -> None:
            self._turn = 0
            self.seen: list[list[message.Message]] = []

        def stream(
            self,
            messages: Sequence[message.Message],
            tools: Sequence[tool.Tool] = (),
        ) -> Iterator[streaming.Event]:
            self.seen.append(list(messages))
            self._turn += 1
            if self._turn == 1:
                yield streaming.ToolUse(id="t1", name="test__add", input={"a": 2, "b": 2})
                yield streaming.MessageCompleted(text="", stop_reason="tool_use")
            else:
                yield streaming.TextDelta("the sum is 4")
                yield streaming.MessageCompleted(
                    text="the sum is 4", stop_reason="end_turn"
                )

    model = _ToolThenAnswer()
    chat_agent = agent.Agent(model, extensions=[extension.Extension("test", [adder])])

    async def gather() -> list[streaming.Event]:
        return [event async for event in chat_agent.events(_stream(["add 2 and 2"]))]

    events = asyncio.run(gather())

    assert ran == [{"a": 2, "b": 2}]
    assert events[-1] == streaming.MessageCompleted(
        text="the sum is 4", stop_reason="end_turn"
    )
    assert model.seen[1] == [
        message.Message(message.Role.USER, [message.Text("add 2 and 2")]),
        message.Message(
            message.Role.ASSISTANT,
            [message.ToolCall("t1", "test__add", {"a": 2, "b": 2})],
        ),
        message.Message(message.Role.USER, [message.ToolResult("t1", "4")]),
    ]


def test_runs_every_tool_requested_in_one_turn() -> None:
    ran: list[tuple[str, dict[str, object]]] = []

    def make(name: str):
        def run(args: dict[str, object]) -> str:
            ran.append((name, args))
            return f"{name}-done"

        return run

    first = tool.Tool("first", "First.", {}, make("first"))
    second = tool.Tool("second", "Second.", {}, make("second"))
    model = _TurnModel(
        [
            [
                streaming.ToolUse(id="c1", name="test__first", input={"x": 1}),
                streaming.ToolUse(id="c2", name="test__second", input={"y": 2}),
                streaming.MessageCompleted(text="", stop_reason="tool_use"),
            ],
            [streaming.MessageCompleted(text="done", stop_reason="end_turn")],
        ]
    )
    chat_agent = agent.Agent(model, extensions=[extension.Extension("test", [first, second])])

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["go"])):
            pass

    asyncio.run(gather())

    assert ran == [("first", {"x": 1}), ("second", {"y": 2})]
    assert model.seen[1] == [
        message.Message(message.Role.USER, [message.Text("go")]),
        message.Message(
            message.Role.ASSISTANT,
            [
                message.ToolCall("c1", "test__first", {"x": 1}),
                message.ToolCall("c2", "test__second", {"y": 2}),
            ],
        ),
        message.Message(
            message.Role.USER,
            [
                message.ToolResult("c1", "first-done"),
                message.ToolResult("c2", "second-done"),
            ],
        ),
    ]


def test_assistant_turn_keeps_text_before_tool_calls() -> None:
    only = tool.Tool("only", "Only.", {}, lambda args: "ok")
    model = _TurnModel(
        [
            [
                streaming.TextDelta("let me check"),
                streaming.ToolUse(id="c1", name="test__only", input={}),
                streaming.MessageCompleted(text="let me check", stop_reason="tool_use"),
            ],
            [streaming.MessageCompleted(text="final", stop_reason="end_turn")],
        ]
    )
    chat_agent = agent.Agent(model, extensions=[extension.Extension("test", [only])])

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["go"])):
            pass

    asyncio.run(gather())

    assert chat_agent.conversation.history[1] == message.Message(
        message.Role.ASSISTANT,
        [message.Text("let me check"), message.ToolCall("c1", "test__only", {})],
    )


def test_command_stops_without_recording_it() -> None:
    model = _ScriptedModel(["hi there"])
    chat_agent = agent.Agent(model)

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["hello", "/quit"])):
            pass

    asyncio.run(gather())

    assert chat_agent.conversation.history == [
        message.Message(message.Role.USER, [message.Text("hello")]),
        message.Message(message.Role.ASSISTANT, [message.Text("hi there")]),
    ]


def test_each_turn_includes_prior_turns() -> None:
    model = _ScriptedModel(["first reply", "second reply"])
    chat_agent = agent.Agent(model)

    async def gather() -> None:
        async for _ in chat_agent.events(_stream(["first question", "second question"])):
            pass

    asyncio.run(gather())

    assert model.seen[0] == [
        message.Message(message.Role.USER, [message.Text("first question")]),
    ]
    assert model.seen[1] == [
        message.Message(message.Role.USER, [message.Text("first question")]),
        message.Message(message.Role.ASSISTANT, [message.Text("first reply")]),
        message.Message(message.Role.USER, [message.Text("second question")]),
    ]
