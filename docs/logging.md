# Logging

## MCP server log

A stdio MCP server runs as a child process. `McpToolServer` (`infra/mcp_server.py`) captures its error output to `mcp-server.log` under the [inloop directory](../README.md#setup)'s `log` subdirectory, shared across servers.
