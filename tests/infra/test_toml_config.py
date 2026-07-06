"""Tests for reading composed application configuration from a TOML file."""

from pathlib import Path

from inloop.infra.toml_config import TomlConfig


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "inloop.toml"
    path.write_text(body)
    return path


def test_reads_each_section_into_its_own_sub_config(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
        [mcp.servers.deepwiki]
        url = "https://mcp.deepwiki.com/mcp"
        """,
    )
    config = TomlConfig(path)

    assert list(config.mcp.load()) == ["deepwiki"]


def test_config_without_telegram_still_reads_the_other_sections(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
        [mcp.servers.deepwiki]
        url = "https://mcp.deepwiki.com/mcp"
        """,
    )
    config = TomlConfig(path)

    assert list(config.mcp.load()) == ["deepwiki"]


def test_absent_file_falls_back_to_defaults(tmp_path: Path) -> None:
    config = TomlConfig(tmp_path / "missing.toml")

    assert config.mcp.load() == {}


def test_expands_tilde_in_mcp_args(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", "/test/home")
    path = _write(
        tmp_path,
        """
        [mcp.servers.playwright]
        command = "npx"
        args = ["--output-dir", "~/playwright-mcp"]
        """,
    )
    config = TomlConfig(path)

    servers = config.mcp.load()
    assert servers["playwright"]._args == ["--output-dir", "/test/home/playwright-mcp"]
