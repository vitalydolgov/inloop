"""Tool servers read from a conventional MCP JSON configuration file."""

import json
import os
from pathlib import Path

from inloop.app.tool_server import ToolServer
from inloop.infra.mcp_server import McpToolServer


class McpJsonConfig:
    """Tool servers declared under the `mcpServers` object of an MCP JSON file."""

    def __init__(self, path: Path):
        self._path = path

    def load(self) -> dict[str, ToolServer]:
        """Return a tool server for each entry under `mcpServers`, reading the file afresh."""
        servers = {}
        for name, entry in self._servers().items():
            servers[name] = McpToolServer(
                command=entry.get("command"),
                args=_expand_paths(entry.get("args")),
                env=entry.get("env"),
                cwd=_expand_path(entry.get("cwd")),
                url=entry.get("url"),
            )
        return servers

    def _servers(self):
        if not self._path.exists():
            return {}
        data = json.loads(self._path.read_text())
        return data.get("mcpServers", {})


def _expand_paths(args):
    if args is None:
        return None
    expanded = []
    for arg in args:
        expanded.append(os.path.expanduser(arg))
    return expanded


def _expand_path(path):
    if path is None:
        return None
    return os.path.expanduser(path)
