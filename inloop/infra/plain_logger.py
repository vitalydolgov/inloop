"""Logger that appends plain `time {payload}` lines to a file."""

import datetime
import json
from pathlib import Path

from inloop.app import log
from inloop.domain import streaming


class PlainLogger:
    """A Logger that appends one `time {payload}` line per entry to a file of its own per run."""

    def __init__(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        run_id = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
        self._path = directory / f"{run_id}.log"
        self._thinking = ""
        self._text = ""

    def _payload(self, entry: log.Entry) -> dict[str, object] | None:
        """Render a log entry as a JSON-serializable payload, tagged with its type."""
        match entry:
            case log.UserMessage(text):
                return {"type": "user_message", "text": text}
            case log.ToolResult(call, content):
                return {
                    "type": "tool_result",
                    "tool_call_id": call.id,
                    "name": call.name,
                    "content": content,
                }
            case streaming.ThinkingDelta(text):
                self._thinking += text
                return None
            case streaming.TextDelta(text):
                self._text += text
                return None
            case streaming.ThinkingPhase.ENDED:
                text, self._thinking = self._thinking, ""
                return {"type": "thinking_phase", "phase": entry.value, "text": text}
            case streaming.ThinkingPhase():
                return {"type": "thinking_phase", "phase": entry.value}
            case streaming.TextPhase.ENDED:
                text, self._text = self._text, ""
                return {"type": "text_phase", "phase": entry.value, "text": text}
            case streaming.TextPhase():
                return {"type": "text_phase", "phase": entry.value}
            case streaming.ToolUse(id, name, input):
                return {"type": "tool_use", "id": id, "name": name, "input": input}
            case streaming.MessageCompleted(text, stop_reason):
                return {"type": "message_completed", "stop_reason": stop_reason}

    def log(self, entry: log.Entry) -> None:
        """Append the entry as a timestamped `time {payload}` line, folding streamed deltas into their phase's end."""
        payload = self._payload(entry)
        if payload is None:
            return
        time = datetime.datetime.now(datetime.UTC).isoformat()
        with self._path.open("a") as f:
            f.write(f"{time} {json.dumps(payload)}\n")
