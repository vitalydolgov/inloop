"""Port for reading Telegram bot configuration."""

from typing import Protocol


class TelegramConfig(Protocol):
    """Reads the settings for the Telegram bot."""

    def bot_token(self) -> str:
        """Return the Telegram bot's API token."""
        ...

    def webhook_url(self) -> str:
        """Return the public URL Telegram should deliver updates to."""
        ...

    def webhook_path(self) -> str:
        """Return the route the bot listens on."""
        ...
