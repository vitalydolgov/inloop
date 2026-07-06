# Configuration

Settings are read from a single TOML file — `inloop.toml` by default, overridable with `INLOOP_CONFIG`. Copy `inloop.toml.example` to `inloop.toml` to get started. When the file is absent, every section falls back to its defaults.

Provider API keys stay in the environment, loaded from a `.env` file if present, since they are secrets rather than settings — each provider reads its own key, e.g. `ANTHROPIC_API_KEY`. See [Providers](providers.md).

## Sections

The file is composed of one table per concern, each read into its own sub-config:

- `[extensions]` — `path` is the directory where installed extensions are stored, defaulting to `var/extensions`. See [Extensions](extensions.md).
- `[mcp.servers]` — one entry per MCP server to mount. See [MCP servers](mcp.md).
- `[telegram]` — `bot_token` and `webhook_url` for the Telegram bot. See [Telegram](telegram.md).

```toml
[extensions]
path = "var/extensions"

[mcp.servers.deepwiki]
url = "https://mcp.deepwiki.com/mcp"

[telegram]
bot_token = "..."
webhook_url = "https://..."
```

## Adding an option

Each section is a sub-config behind its own port — `ExtensionsConfig` and `Config` in `app/config.py`, `TelegramConfig` in `demo/telegram/config.py`. Add a method to the port and read the value in the matching section of `TomlConfig` (`infra/toml_config.py`).
