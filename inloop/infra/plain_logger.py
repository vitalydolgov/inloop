"""Logger that appends plain `time {payload}` lines to a file."""

import datetime
import json
from pathlib import Path

from inloop.app import logger
from inloop.domain import message
from inloop.domain import streaming


class PlainLogger:
    """A Logger that appends one `time {payload}` line per entry to a file of its own per run."""

    def __init__(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        run_id = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
        self._path = directory / f"{run_id}.log"
        self._thinking: dict[str, str] = {}
        self._text: dict[str, str] = {}

    def _block(self, block):
        match block:
            case message.Text(text):
                return {"type": "text", "text": text}
            case message.ToolCall(id, name, input):
                return {"type": "tool_call", "id": id, "name": name, "input": input}
            case message.ToolSuccess(tool_call_id, content):
                return {
                    "type": "tool_result",
                    "tool_call_id": tool_call_id,
                    "content": content,
                }
            case message.ToolFailure(tool_call_id, content):
                return {
                    "type": "tool_error",
                    "tool_call_id": tool_call_id,
                    "content": content,
                }

    def _payload(self, entry, agent_id):
        match entry:
            case message.Message(role, content):
                return {
                    "type": "message",
                    "role": role.value,
                    "content": [self._block(block) for block in content],
                }
            case streaming.ThinkingDelta(text):
                self._thinking[agent_id] = self._thinking.get(agent_id, "") + text
                return None
            case streaming.TextDelta(text):
                self._text[agent_id] = self._text.get(agent_id, "") + text
                return None
            case streaming.ThinkingPhase.ENDED:
                text = self._thinking.pop(agent_id, "")
                return {"type": "thinking_phase", "phase": entry.value, "text": text}
            case streaming.ThinkingPhase():
                return {"type": "thinking_phase", "phase": entry.value}
            case streaming.TextPhase.ENDED:
                text = self._text.pop(agent_id, "")
                return {"type": "text_phase", "phase": entry.value, "text": text}
            case streaming.TextPhase():
                return {"type": "text_phase", "phase": entry.value}
            case streaming.ToolUse(id, name, input):
                return {"type": "tool_use", "id": id, "name": name, "input": input}
            case streaming.MessageCompleted(text, stop_reason):
                return {"type": "message_completed", "stop_reason": stop_reason}
            case streaming.Interrupted():
                text = self._text.pop(agent_id, "")
                return {"type": "interrupted", "text": text}
            case streaming.Failed(error):
                text = self._text.pop(agent_id, "")
                return {"type": "failed", "error": error, "text": text}

    async def log(self, entry: logger.Entry, agent_id: str = "main") -> None:
        """Append the entry as a timestamped `time {payload}` line, folding streamed deltas into their phase's end."""
        payload = self._payload(entry, agent_id)
        if payload is None:
            return
        payload = {"agent_id": agent_id, **payload}
        time = datetime.datetime.now(datetime.UTC).isoformat()
        with self._path.open("a") as f:
            f.write(f"{time} {json.dumps(payload)}\n")
