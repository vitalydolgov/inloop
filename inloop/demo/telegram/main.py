"""Run the Telegram bot, serving the agent over a webhook."""

import asyncio
import hashlib
import os
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
from aiohttp import web

from inloop.app.agent import Agent
from inloop.infra.directory_registry import DirectoryExtensionRegistry
from inloop.infra.env_config import EnvConfig
from inloop.infra.plain_logger import PlainLogger
from inloop.demo.telegram.client import TelegramClient
from inloop.demo.telegram.config import TelegramConfig
from inloop.demo.telegram.server import create_app

DEFAULT_PORT = 8080


def _secret_token(bot_token: str) -> str:
    return hashlib.sha256(bot_token.encode()).hexdigest()


async def _run() -> None:
    import anthropic
    from inloop.infra import providers

    model = providers.anthropic.AnthropicModel(
        anthropic.Anthropic(),
        model="claude-sonnet-5",
        max_tokens=64_000,
        effort="low",
    )
    config = EnvConfig()
    registry = DirectoryExtensionRegistry(config.extensions_path())
    logger = PlainLogger(Path("var/log"))
    agent = Agent(model, extensions=registry.load(), logger=logger)

    telegram_config = TelegramConfig()
    secret_token = _secret_token(telegram_config.bot_token())

    async with aiohttp.ClientSession() as session:
        client = TelegramClient(session, telegram_config.bot_token())
        await client.set_webhook(telegram_config.webhook_url(), secret_token)

        app = create_app(agent, client, telegram_config, secret_token)
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.environ.get("PORT", DEFAULT_PORT))
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        path = urlparse(telegram_config.webhook_url()).path
        print(f"Listening on 0.0.0.0:{port}{path}")
        await asyncio.Event().wait()


def main() -> None:
    """Start the Telegram bot webhook server."""
    asyncio.run(_run())
