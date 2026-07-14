# Configuration

Configuration is split across two independent files:

- `config.toml` contains the agent model, the optional subagent model, and Telegram settings.
- `mcp.json` contains the [MCP](https://modelcontextprotocol.io) servers whose tools are available to the agent.

Both files are optional. If `config.toml` is absent, its settings use their defaults; if `mcp.json` is absent, no MCP servers are loaded.

## File locations

The application looks up each file independently:

| File | Project-specific | User-wide |
| --- | --- | --- |
| Agent, subagent, and Telegram settings | `./config.toml` | `~/.inloop/config.toml` |
| MCP servers | `./mcp.json` | `~/.inloop/mcp.json` |

A project-specific file takes precedence over the user-wide file with the same name. The files are not merged: a local `config.toml` does not affect which `mcp.json` is selected, and vice versa. Set `INLOOP_HOME` to use a different directory instead of `~/.inloop` for user-wide settings.

## `config.toml`

The TOML file contains these sections:

- `[agent.model]` — the `provider` the agent runs on and that provider's settings. See [Providers](providers.md).
- `[subagent.model]` — an optional distinct provider for spawned subagents, with the same shape as `[agent.model]`; when omitted, subagents reuse the agent's model. See [Providers](providers.md).
- `[telegram]` — `bot_token` and `webhook_url` for the Telegram bot. See [Telegram](telegram.md).

Example:

```toml
[agent.model]
provider = "anthropic"
model = "claude-sonnet-5"
max_tokens = 64000
context_window = 200000
effort = "medium"

[telegram]
bot_token = "..."
webhook_url = "https://..."
```

## `mcp.json`

MCP servers are declared under the conventional top-level `mcpServers` object. Each key is the name used to mount that server's tools. See [MCP servers](mcp.md) for the supported transports and fields.

Example:

```json
{
  "mcpServers": {
    "deepwiki": {
      "url": "https://mcp.deepwiki.com/mcp"
    }
  }
}
```
