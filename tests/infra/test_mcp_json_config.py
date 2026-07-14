"""Tests for reading tool servers from a conventional MCP JSON configuration file."""

from pathlib import Path

from inloop.infra.mcp_json_config import McpJsonConfig


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "mcp.json"
    path.write_text(body)
    return path


def test_reads_http_server_options(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
        {
          "mcpServers": {
            "deepwiki": {
              "url": "https://mcp.deepwiki.com/mcp"
            }
          }
        }
        """,
    )
    config = McpJsonConfig(path)

    server = config.load()["deepwiki"]

    assert server._url == "https://mcp.deepwiki.com/mcp"
    assert server._command is None
    assert server._args == []
    assert server._env is None
    assert server._cwd is None


def test_absent_file_falls_back_to_empty(tmp_path: Path) -> None:
    config = McpJsonConfig(tmp_path / "missing.json")

    assert config.load() == {}


def test_expands_tilde_in_args_and_cwd(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", "/test/home")
    path = _write(
        tmp_path,
        """
        {
          "mcpServers": {
            "playwright": {
              "command": "npx",
              "args": ["--output-dir", "~/playwright-mcp"],
              "env": {
                "PLAYWRIGHT_BROWSERS_PATH": "~/browsers"
              },
              "cwd": "~/work"
            }
          }
        }
        """,
    )
    config = McpJsonConfig(path)

    servers = config.load()
    server = servers["playwright"]

    assert server._command == "npx"
    assert server._args == ["--output-dir", "/test/home/playwright-mcp"]
    assert server._env == {"PLAYWRIGHT_BROWSERS_PATH": "~/browsers"}
    assert server._cwd == "/test/home/work"
    assert server._url is None


def test_load_rereads_the_file_through_a_held_config(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
        {
          "mcpServers": {
            "deepwiki": {
              "url": "https://mcp.deepwiki.com/mcp"
            }
          }
        }
        """,
    )
    config = McpJsonConfig(path)

    assert list(config.load()) == ["deepwiki"]

    path.write_text('{"mcpServers": {}}')

    assert config.load() == {}


def test_load_picks_up_added_and_replaced_servers(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
        {
          "mcpServers": {
            "old": {
              "url": "https://old.example/mcp"
            }
          }
        }
        """,
    )
    config = McpJsonConfig(path)

    path.write_text(
        """
        {
          "mcpServers": {
            "new": {
              "url": "https://new.example/mcp"
            }
          }
        }
        """
    )

    assert list(config.load()) == ["new"]
