"""Tests for reading composed application configuration from a TOML file."""

from pathlib import Path

from inloop.infra.toml_config import TomlConfig


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(body)
    return path


def test_absent_file_falls_back_to_defaults(tmp_path: Path) -> None:
    config = TomlConfig(tmp_path / "missing.toml")

    assert config.agent.model() is None
    assert config.subagent.model() is None


def test_reads_telegram_section(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
        [telegram]
        bot_token = "tok"
        webhook_url = "https://example.com/hook"
        """,
    )
    config = TomlConfig(path)

    assert config.telegram.bot_token() == "tok"
    assert config.telegram.webhook_url() == "https://example.com/hook"
    assert config.telegram.webhook_path() == "/hook"
