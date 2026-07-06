"""Reads configuration from environment variables, loading a .env file if present."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_EXTENSIONS_PATH = "var/extensions"
INLOOP_MCP_CONFIG_DEFAULT = "mcp.json"


class EnvConfig:
    """A Config that reads values from environment variables."""

    def extensions_path(self) -> Path:
        """Return the directory where installed extensions are stored."""
        return Path(os.environ.get("EXTENSIONS_PATH", DEFAULT_EXTENSIONS_PATH))

    def mcp_config_path(self) -> Path:
        """Return the path to the MCP servers configuration file."""
        return Path(os.environ.get("INLOOP_MCP_CONFIG", INLOOP_MCP_CONFIG_DEFAULT))
