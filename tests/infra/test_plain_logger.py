"""Tests for the plain-text per-run logger."""

import json
import re
from datetime import datetime
from pathlib import Path

from inloop.app import logger
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


def test_creates_the_directory_and_a_run_named_file(tmp_path: Path) -> None:
    directory = tmp_path / "logs"
    plain_logger = PlainLogger(directory)

    assert directory.is_dir()

    plain_logger.log(logger.UserMessage("hello"))

    [logfile] = list(directory.iterdir())
    assert RUN_FILENAME.match(logfile.name)


def test_logs_a_user_message(tmp_path: Path) -> None:
    plain_logger = PlainLogger(tmp_path)

    plain_logger.log(logger.UserMessage("hello"))

    [(time, payload)] = _entries(tmp_path)
    datetime.fromisoformat(time)
    assert payload == {"type": "user_message", "text": "hello"}


def test_logs_a_tool_result(tmp_path: Path) -> None:
    plain_logger = PlainLogger(tmp_path)

    call = message.ToolCall("t1", "test__add", {"a": 2, "b": 2})
    plain_logger.log(logger.ToolResult(call, "4"))

    [(_, payload)] = _entries(tmp_path)
    assert payload == {
        "type": "tool_result",
        "tool_call_id": "t1",
        "name": "test__add",
        "content": "4",
    }


def test_logs_thinking_and_text_phase_markers(tmp_path: Path) -> None:
    plain_logger = PlainLogger(tmp_path)

    plain_logger.log(streaming.ThinkingPhase.STARTED)
    plain_logger.log(streaming.ThinkingPhase.ENDED)
    plain_logger.log(streaming.TextPhase.STARTED)
    plain_logger.log(streaming.TextPhase.ENDED)

    assert [payload for _, payload in _entries(tmp_path)] == [
        {"type": "thinking_phase", "phase": "started"},
        {"type": "thinking_phase", "phase": "ended", "text": ""},
        {"type": "text_phase", "phase": "started"},
        {"type": "text_phase", "phase": "ended", "text": ""},
    ]


def test_logs_tool_use_and_message_completed(tmp_path: Path) -> None:
    plain_logger = PlainLogger(tmp_path)

    plain_logger.log(streaming.ToolUse(id="t1", name="test__add", input={"a": 2, "b": 2}))
    plain_logger.log(streaming.MessageCompleted(text="4", stop_reason="end_turn"))

    assert [payload for _, payload in _entries(tmp_path)] == [
        {
            "type": "tool_use",
            "id": "t1",
            "name": "test__add",
            "input": {"a": 2, "b": 2},
        },
        {"type": "message_completed", "text": "4", "stop_reason": "end_turn"},
    ]


def test_folds_deltas_into_their_phase_end(tmp_path: Path) -> None:
    plain_logger = PlainLogger(tmp_path)

    plain_logger.log(streaming.ThinkingPhase.STARTED)
    plain_logger.log(streaming.ThinkingDelta("rea"))
    plain_logger.log(streaming.ThinkingDelta("soning"))
    plain_logger.log(streaming.ThinkingPhase.ENDED)
    plain_logger.log(streaming.TextPhase.STARTED)
    plain_logger.log(streaming.TextDelta("re"))
    plain_logger.log(streaming.TextDelta("ply"))
    plain_logger.log(streaming.TextPhase.ENDED)

    assert [payload for _, payload in _entries(tmp_path)] == [
        {"type": "thinking_phase", "phase": "started"},
        {"type": "thinking_phase", "phase": "ended", "text": "reasoning"},
        {"type": "text_phase", "phase": "started"},
        {"type": "text_phase", "phase": "ended", "text": "reply"},
    ]


def test_resets_the_buffer_after_each_phase(tmp_path: Path) -> None:
    plain_logger = PlainLogger(tmp_path)

    plain_logger.log(streaming.ThinkingPhase.STARTED)
    plain_logger.log(streaming.ThinkingDelta("first"))
    plain_logger.log(streaming.ThinkingPhase.ENDED)
    plain_logger.log(streaming.ThinkingPhase.STARTED)
    plain_logger.log(streaming.ThinkingPhase.ENDED)

    assert [payload for _, payload in _entries(tmp_path)] == [
        {"type": "thinking_phase", "phase": "started"},
        {"type": "thinking_phase", "phase": "ended", "text": "first"},
        {"type": "thinking_phase", "phase": "started"},
        {"type": "thinking_phase", "phase": "ended", "text": ""},
    ]


def test_appends_entries_in_order(tmp_path: Path) -> None:
    plain_logger = PlainLogger(tmp_path)

    plain_logger.log(logger.UserMessage("first"))
    plain_logger.log(logger.UserMessage("second"))

    assert [payload for _, payload in _entries(tmp_path)] == [
        {"type": "user_message", "text": "first"},
        {"type": "user_message", "text": "second"},
    ]
