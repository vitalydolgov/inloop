"""Port for reading application configuration."""

from pathlib import Path
from typing import Protocol


class Config(Protocol):
    """Reads application configuration."""

    def extensions_path(self) -> Path:
        """Return the directory where installed extensions are stored."""
        ...

    def mcp_config_path(self) -> Path:
        """Return the path to the MCP servers configuration file."""
        ...
