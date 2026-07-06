# Configuration

The application reads its settings from a single TOML file, one table per concern. This document covers where those settings come from and the sections you can set; each section links to its own page for the details. When the file is absent, every section falls back to its defaults. See [Setup](../README.md#setup) for where the file lives and how to create one.

## Specification

- `[mcp.servers]` — one entry per MCP server to mount. See [MCP servers](mcp.md).
- `[telegram]` — `bot_token` and `webhook_url` for the Telegram bot. See [Telegram](telegram.md).

## Example

```toml
[mcp.servers.deepwiki]
url = "https://mcp.deepwiki.com/mcp"

[telegram]
bot_token = "..."
webhook_url = "https://..."
```
