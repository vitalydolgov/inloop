"""Port for exposing an extension's tools to external clients, and the workflow that drives it."""

from typing import Protocol

from inloop.app.extensions import ExtensionRegistry
from inloop.domain import extension


class ToolPublisher(Protocol):
    """Runs a server that exposes an extension's tools to external clients, such as an MCP server."""

    async def run(self, ext: extension.Extension) -> None:
        """Serve the extension's tools until the transport closes."""
        ...


async def serve(registry: ExtensionRegistry, name: str, publisher: ToolPublisher):
    """Look up the named installed extension and expose its tools through the publisher."""
    extensions = {ext.name: ext for ext in registry.load()}
    if name not in extensions:
        raise LookupError(name)
    await publisher.run(extensions[name])
