"""Minimal MCP server whose tool always fails with a specific message.

Used to verify that tool errors are reported back to the model so it can retry.
"""

import asyncio

from mcp.server import FastMCP

mcp = FastMCP("inloop-test-fail")


@mcp.tool()
def flaky() -> str:
    """A tool that always fails so the agent sees an error result."""
    raise RuntimeError


if __name__ == "__main__":
    asyncio.run(mcp.run_stdio_async())
