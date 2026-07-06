"""Application configuration read from a single TOML file, composed section by section."""

import os
import tomllib
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from inloop.app.tool_server import ToolServer
from inloop.infra.mcp_server import McpToolServer

load_dotenv()

DEFAULT_CONFIG_PATH = "inloop.toml"
DEFAULT_EXTENSIONS_PATH = "var/extensions"
DEFAULT_WEBHOOK_PATH = "/webhook"


def default_path() -> Path:
    """Return the configuration file path, overridable with `INLOOP_CONFIG`."""
    return Path(os.environ.get("INLOOP_CONFIG", DEFAULT_CONFIG_PATH))


class ExtensionsSection:
    """Extension settings read from the `[extensions]` table."""

    def __init__(self, table):
        self._table = table

    def path(self) -> Path:
        """Return the directory where installed extensions are stored."""
        return Path(self._table.get("path", DEFAULT_EXTENSIONS_PATH))


class McpSection:
    """Tool servers declared under the `[mcp.servers]` table."""

    def __init__(self, table):
        self._table = table

    def load(self) -> dict[str, ToolServer]:
        """Return a tool server for each entry under `[mcp.servers]`."""
        return {
            name: McpToolServer(
                command=entry.get("command"),
                args=entry.get("args"),
                env=entry.get("env"),
                url=entry.get("url"),
            )
            for name, entry in self._table.items()
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


class TomlConfig:
    """Application configuration composed from the sections of a TOML file."""

    def __init__(self, path: Path):
        data = tomllib.loads(path.read_text()) if path.exists() else {}
        self.extensions = ExtensionsSection(data.get("extensions", {}))
        self.mcp = McpSection(data.get("mcp", {}).get("servers", {}))
        self.telegram = TelegramSection(data.get("telegram", {}))
