"""Resolves where the app keeps its config file, logs, and installed extensions."""

import os
from pathlib import Path

CONFIG_NAME = "config.toml"
MCP_CONFIG_NAME = "mcp.json"
DEFAULT_HOME = "~/.inloop"


def config_path() -> Path:
    """Return the configuration file path, preferring one in the working directory."""
    local = Path(CONFIG_NAME)
    if local.exists():
        return local
    return _home() / CONFIG_NAME


def mcp_config_path() -> Path:
    """Return the MCP servers configuration file path, preferring one in the working directory."""
    local = Path(MCP_CONFIG_NAME)
    if local.exists():
        return local
    return _home() / MCP_CONFIG_NAME


def log_dir() -> Path:
    """Return the directory run logs are written to."""
    return _home() / "log"


def extensions_dir() -> Path:
    """Return the directory installed extensions are stored in."""
    return _home() / "extensions"


def _home():
    return Path(os.environ.get("INLOOP_HOME", DEFAULT_HOME)).expanduser()
