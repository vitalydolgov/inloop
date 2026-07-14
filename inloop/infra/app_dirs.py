"""Resolves where the app keeps its config file and logs."""

import os
from pathlib import Path
from typing import Literal

CONFIG_NAME = "config.toml"
MCP_CONFIG_NAME = "mcp.json"
AGENTS_FILE_NAME = "AGENTS.md"
DEFAULT_HOME = "~/.inloop"


def config_path() -> Path:
    """Return the user-wide application configuration file path."""
    return _home() / CONFIG_NAME


def mcp_config_path() -> Path:
    """Return the user-wide MCP servers configuration file path."""
    return _home() / MCP_CONFIG_NAME


def agents_file_path(
    instructions: Literal["auto", "user"] = "auto",
) -> Path:
    """Return the agent instructions path from the selected location."""
    local = Path(AGENTS_FILE_NAME)
    user = _home() / AGENTS_FILE_NAME
    if instructions == "user":
        return user
    if local.exists():
        return local
    return user


def log_dir() -> Path:
    """Return the directory run logs are written to."""
    return _home() / "log"


def _home():
    return Path(os.environ.get("INLOOP_HOME", DEFAULT_HOME)).expanduser()
