"""Ports for reading application configuration, composed a section per concern."""

from pathlib import Path
from typing import Protocol

from inloop.app.tool_server import ToolServerSource


class ExtensionsConfig(Protocol):
    """Reads the settings for installed extensions."""

    def path(self) -> Path:
        """Return the directory where installed extensions are stored."""
        ...


class Config(Protocol):
    """Application configuration composed of a section per concern."""

    extensions: ExtensionsConfig
    mcp: ToolServerSource
