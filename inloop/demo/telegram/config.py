"""Reads Telegram bot configuration from environment variables."""

import os
from urllib.parse import urlparse

DEFAULT_WEBHOOK_PATH = "/webhook"


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

    def webhook_path(self) -> str:
        """Return the route the bot listens on, defaulting when no webhook URL is set."""
        url = os.environ.get("TELEGRAM_WEBHOOK_URL")
        return urlparse(url).path if url else DEFAULT_WEBHOOK_PATH
