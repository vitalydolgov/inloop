"""Application configuration read from a single TOML file, composed section by section."""

import os
import tomllib
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from inloop.app.tool_server import ToolServer
from inloop.infra.mcp_server import McpToolServer
from inloop.infra.providers import factory

load_dotenv()

DEFAULT_WEBHOOK_PATH = "/webhook"


class ModelSection:
    """The model a role runs on, read from its `[<role>.model]` table."""

    def __init__(self, table):
        self._table = table

    def model(self):
        """Return the configured model, or None when none is declared."""
        if not self._table:
            return None
        settings = dict(self._table)
        provider = settings.pop("provider")
        return factory.create_model(provider, settings)


class McpSection:
    """Tool servers declared under the `[mcp.servers]` table."""

    def __init__(self, servers):
        self._servers = servers

    def load(self) -> dict[str, ToolServer]:
        """Return a tool server for each entry under `[mcp.servers]`, reading the file afresh."""
        return {
            name: McpToolServer(
                command=entry.get("command"),
                args=_expand_paths(entry.get("args")),
                env=entry.get("env"),
                cwd=entry.get("cwd"),
                url=entry.get("url"),
            )
            for name, entry in self._servers().items()
        }


class TelegramSection:
    """Telegram bot settings read from the `[telegram]` table."""

    def __init__(self, table):
        self._table = table

    def bot_token(self) -> str:
        """Return the Telegram bot's API token."""
        return self._table["bot_token"]

    def webhook_url(self) -> str:
        """Return the public URL Telegram should deliver updates to."""
        return self._table["webhook_url"]

    def webhook_path(self) -> str:
        """Return the route the bot listens on, defaulting when no webhook URL is set."""
        url = self._table.get("webhook_url")
        return urlparse(url).path if url else DEFAULT_WEBHOOK_PATH


def _expand_paths(args):
    """Expand leading ~ in each argument to the user's home directory."""
    if args is None:
        return None
    return [os.path.expanduser(arg) for arg in args]


class TomlConfig:
    """Application configuration composed from the sections of a TOML file, read afresh on each access."""

    def __init__(self, path: Path):
        self._path = path

    @property
    def agent(self) -> ModelSection:
        """The model the agent runs on."""
        return ModelSection(self._data.get("agent", {}).get("model"))

    @property
    def subagent(self) -> ModelSection:
        """The model spawned subagents run on."""
        return ModelSection(self._data.get("subagent", {}).get("model"))

    @property
    def mcp(self) -> McpSection:
        """The tool servers the agent connects to."""
        return McpSection(lambda: self._data.get("mcp", {}).get("servers", {}))

    @property
    def telegram(self) -> TelegramSection:
        """The Telegram bot's settings."""
        return TelegramSection(self._data.get("telegram", {}))

    @property
    def _data(self):
        return tomllib.loads(self._path.read_text()) if self._path.exists() else {}
