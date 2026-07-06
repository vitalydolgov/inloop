"""Integration tests that talk to the real DeepWiki MCP server."""

import asyncio

import pytest

pytest.importorskip("mcp")

from inloop.infra.mcp_server import McpToolServer

pytestmark = pytest.mark.deepwiki

URL = "https://mcp.deepwiki.com/mcp"
REPO = "fastapi/fastapi"


def _run(coro):
    return asyncio.run(coro)


def test_lists_deepwiki_tools() -> None:
    server = McpToolServer(url=URL)

    async def check():
        await server.connect()
        try:
            tools = await server.list_tools()
            names = {t.name for t in tools}
            assert "read_wiki_structure" in names
            assert "read_wiki_contents" in names
            assert "ask_question" in names
        finally:
            await server.aclose()

    _run(check())


def test_reads_wiki_structure_for_a_repo() -> None:
    server = McpToolServer(url=URL)

    async def check():
        await server.connect()
        try:
            result = await server.call_tool("read_wiki_structure", {"repo": REPO})
            assert isinstance(result, str)
            assert len(result) > 0
        finally:
            await server.aclose()

    _run(check())
