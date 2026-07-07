"""Tests for the plain-text per-run logger."""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path

from inloop.domain import message
from inloop.domain import streaming
from inloop.infra.plain_logger import PlainLogger

RUN_FILENAME = re.compile(r"^\d{8}T\d{6}Z\.log$")


def _entries(directory: Path) -> list[tuple[str, dict]]:
    """Read the run's single log file and parse each `time {payload}` line."""
    [path] = list(directory.glob("*.log"))
    parsed = []
    for line in path.read_text().splitlines():
        time, _, payload = line.partition(" ")
        parsed.append((time, json.loads(payload)))
    return parsed


def _log(plain_logger, *entries):
    async def run():
        for entry in entries:
            await plain_logger.log(entry)

    asyncio.run(run())


def test_creates_the_directory_and_a_run_named_file(tmp_path: Path) -> None:
    directory = tmp_path / "logs"
    plain_logger = PlainLogger(directory)

    assert directory.is_dir()

    _log(plain_logger, message.Message(message.Role.USER, [message.Text("hello")]))

    [logfile] = list(directory.iterdir())
    assert RUN_FILENAME.match(logfile.name)


def test_logs_a_user_message(tmp_path: Path) -> None:
    plain_logger = PlainLogger(tmp_path)

    _log(plain_logger, message.Message(message.Role.USER, [message.Text("hello")]))

    [(time, payload)] = _entries(tmp_path)
    datetime.fromisoformat(time)
    assert payload == {
        "agent_id": "main",
        "type": "message",
        "role": "user",
        "content": [{"type": "text", "text": "hello"}],
    }


def test_logs_an_assistant_message_with_a_tool_call(tmp_path: Path) -> None:
    plain_logger = PlainLogger(tmp_path)

    _log(
        plain_logger,
        message.Message(
            message.Role.ASSISTANT,
            [message.ToolCall("t1", "test__add", {"a": 2, "b": 2})],
        ),
    )

    [(_, payload)] = _entries(tmp_path)
    assert payload == {
        "agent_id": "main",
        "type": "message",
        "role": "assistant",
        "content": [
            {"type": "tool_call", "id": "t1", "name": "test__add", "input": {"a": 2, "b": 2}}
        ],
    }


def test_logs_a_tool_result(tmp_path: Path) -> None:
    plain_logger = PlainLogger(tmp_path)

    _log(
        plain_logger,
        message.Message(message.Role.USER, [message.ToolResult("t1", "4")]),
    )

    [(_, payload)] = _entries(tmp_path)
    assert payload == {
        "agent_id": "main",
        "type": "message",
        "role": "user",
        "content": [{"type": "tool_result", "tool_call_id": "t1", "content": "4"}],
    }


def test_logs_thinking_and_text_phase_markers(tmp_path: Path) -> None:
    plain_logger = PlainLogger(tmp_path)

    _log(
        plain_logger,
        streaming.ThinkingPhase.STARTED,
        streaming.ThinkingPhase.ENDED,
        streaming.TextPhase.STARTED,
        streaming.TextPhase.ENDED,
    )

    assert [payload for _, payload in _entries(tmp_path)] == [
        {"agent_id": "main", "type": "thinking_phase", "phase": "started"},
        {"agent_id": "main", "type": "thinking_phase", "phase": "ended", "text": ""},
        {"agent_id": "main", "type": "text_phase", "phase": "started"},
        {"agent_id": "main", "type": "text_phase", "phase": "ended", "text": ""},
    ]


def test_logs_tool_use_and_message_completed(tmp_path: Path) -> None:
    plain_logger = PlainLogger(tmp_path)

    _log(
        plain_logger,
        streaming.ToolUse(id="t1", name="test__add", input={"a": 2, "b": 2}),
        streaming.MessageCompleted(text="4", stop_reason="end_turn", input_tokens=0),
    )

    assert [payload for _, payload in _entries(tmp_path)] == [
        {
            "agent_id": "main",
            "type": "tool_use",
            "id": "t1",
            "name": "test__add",
            "input": {"a": 2, "b": 2},
        },
        {"agent_id": "main", "type": "message_completed", "stop_reason": "end_turn"},
    ]


def test_folds_deltas_into_their_phase_end(tmp_path: Path) -> None:
    plain_logger = PlainLogger(tmp_path)

    _log(
        plain_logger,
        streaming.ThinkingPhase.STARTED,
        streaming.ThinkingDelta("rea"),
        streaming.ThinkingDelta("soning"),
        streaming.ThinkingPhase.ENDED,
        streaming.TextPhase.STARTED,
        streaming.TextDelta("re"),
        streaming.TextDelta("ply"),
        streaming.TextPhase.ENDED,
    )

    assert [payload for _, payload in _entries(tmp_path)] == [
        {"agent_id": "main", "type": "thinking_phase", "phase": "started"},
        {"agent_id": "main", "type": "thinking_phase", "phase": "ended", "text": "reasoning"},
        {"agent_id": "main", "type": "text_phase", "phase": "started"},
        {"agent_id": "main", "type": "text_phase", "phase": "ended", "text": "reply"},
    ]


def test_resets_the_buffer_after_each_phase(tmp_path: Path) -> None:
    plain_logger = PlainLogger(tmp_path)

    _log(
        plain_logger,
        streaming.ThinkingPhase.STARTED,
        streaming.ThinkingDelta("first"),
        streaming.ThinkingPhase.ENDED,
        streaming.ThinkingPhase.STARTED,
        streaming.ThinkingPhase.ENDED,
    )

    assert [payload for _, payload in _entries(tmp_path)] == [
        {"agent_id": "main", "type": "thinking_phase", "phase": "started"},
        {"agent_id": "main", "type": "thinking_phase", "phase": "ended", "text": "first"},
        {"agent_id": "main", "type": "thinking_phase", "phase": "started"},
        {"agent_id": "main", "type": "thinking_phase", "phase": "ended", "text": ""},
    ]


def test_appends_entries_in_order(tmp_path: Path) -> None:
    plain_logger = PlainLogger(tmp_path)

    _log(
        plain_logger,
        message.Message(message.Role.USER, [message.Text("first")]),
        message.Message(message.Role.USER, [message.Text("second")]),
    )

    assert [payload for _, payload in _entries(tmp_path)] == [
        {
            "agent_id": "main",
            "type": "message",
            "role": "user",
            "content": [{"type": "text", "text": "first"}],
        },
        {
            "agent_id": "main",
            "type": "message",
            "role": "user",
            "content": [{"type": "text", "text": "second"}],
        },
    ]
