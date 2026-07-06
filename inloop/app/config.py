"""Ports for reading application configuration, composed a section per concern."""

from typing import Protocol

from inloop.app.tool_server import ToolServerSource


class Config(Protocol):
    """Application configuration composed of a section per concern."""

    mcp: ToolServerSource
