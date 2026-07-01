"""Async client for the Telegram Bot API."""

import aiohttp

API_URL = "https://api.telegram.org/bot{token}/{method}"


class TelegramClient:
    """Sends messages and registers the webhook for a single Telegram bot."""

    def __init__(self, session: aiohttp.ClientSession, bot_token: str) -> None:
        self._session = session
        self._bot_token = bot_token

    async def set_webhook(self, url: str, secret_token: str) -> None:
        """Register the URL Telegram should POST updates to."""
        await self._call("setWebhook", {"url": url, "secret_token": secret_token})

    async def send_message(self, chat_id: int, html_text: str) -> None:
        """Send an HTML-formatted message to a chat, without a link preview."""
        await self._call(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": html_text,
                "parse_mode": "HTML",
                "link_preview_options": {"is_disabled": True},
            },
        )

    async def _call(self, method: str, payload: dict[str, object]) -> None:
        url = API_URL.format(token=self._bot_token, method=method)
        async with self._session.post(url, json=payload) as response:
            response.raise_for_status()
