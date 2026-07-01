"""Reads Telegram bot configuration from environment variables."""

import os


class TelegramConfig:
    """A config that reads Telegram bot settings from environment variables."""

    def bot_token(self) -> str:
        """Return the Telegram bot's API token."""
        return os.environ["TELEGRAM_BOT_TOKEN"]

    def allowed_user_id(self) -> int:
        """Return the id of the only Telegram user the bot will respond to."""
        return int(os.environ["TELEGRAM_USER_ID"])

    def webhook_url(self) -> str:
        """Return the public URL Telegram should deliver updates to."""
        return os.environ["TELEGRAM_WEBHOOK_URL"]
