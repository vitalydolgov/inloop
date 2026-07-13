"""Port for loading the tool servers the agent is configured to talk to."""

from typing import Protocol

from inloop.app.tool_server import ToolServer


class ToolServerConfig(Protocol):
    """Provides the tool servers configured for the agent, keyed by name."""

    def load(self) -> dict[str, ToolServer]:
        """Return the configured tool servers, keyed by the name each is mounted under."""
        ...
