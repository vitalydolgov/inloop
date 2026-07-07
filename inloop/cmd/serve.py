"""Expose an installed extension's tools as a local MCP server over stdio."""

import asyncio
import sys

from inloop.app import tool_publisher
from inloop.infra import app_dirs
from inloop.infra.directory_registry import DirectoryExtensionRegistry
from inloop.infra.mcp_publisher import McpToolPublisher


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: serve <extension>", file=sys.stderr)
        sys.exit(1)
    name = sys.argv[1]

    registry = DirectoryExtensionRegistry(app_dirs.extensions_dir())
    publisher = McpToolPublisher()
    try:
        asyncio.run(tool_publisher.serve(registry, name, publisher))
    except LookupError:
        print(f"Unknown extension {name!r}", file=sys.stderr)
        sys.exit(1)
