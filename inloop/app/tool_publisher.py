"""Port for exposing installed extensions' tools to external clients, and the workflow that drives it."""

from typing import Protocol

from inloop.app.extensions import ExtensionRegistry
from inloop.domain import extension


class ToolPublisher(Protocol):
    """Runs a server that exposes installed extensions' tools to external clients, such as an MCP server."""

    async def run(self, extensions: list[extension.Extension]) -> None:
        """Serve the extensions' tools until the transport closes."""
        ...


async def serve(registry: ExtensionRegistry, publisher: ToolPublisher):
    """Expose every installed extension's tools through the publisher."""
    await publisher.run(registry.load())
