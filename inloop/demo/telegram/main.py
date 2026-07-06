"""Run the Telegram bot, serving the agent over a webhook."""

import argparse
import asyncio
import hashlib
import os
from pathlib import Path

import aiohttp
from aiohttp import web

from inloop.app import tool_server
from inloop.app.agent import Agent
from inloop.infra import toml_config
from inloop.infra.directory_registry import DirectoryExtensionRegistry
from inloop.infra.plain_logger import PlainLogger
from inloop.demo.telegram.client import TelegramClient
from inloop.demo.telegram.server import create_app

DEFAULT_PORT = 8080


def _secret_token(bot_token: str) -> str:
    return hashlib.sha256(bot_token.encode()).hexdigest()


async def amain():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ngrok", action="store_true", help="expose the webhook through an ngrok tunnel"
    )
    args = parser.parse_args()

    import anthropic
    from inloop.infra import providers

    config = toml_config.TomlConfig(toml_config.default_path())
    async with tool_server.connected(config.mcp) as mcp_extensions:
        registry = DirectoryExtensionRegistry(config.extensions.path())
        agent = Agent(
            model=providers.anthropic.AnthropicModel(
                client=anthropic.AsyncAnthropic(),
                model="claude-sonnet-5",
                max_tokens=64_000,
                effort="medium",
            ),
            extensions=[*registry.load(), *mcp_extensions],
            logger=PlainLogger(Path("var/log")),
        )

        telegram_config = config.telegram
        secret_token = _secret_token(telegram_config.bot_token())
        path = telegram_config.webhook_path()
        port = int(os.environ.get("PORT", DEFAULT_PORT))

        if args.ngrok:
            from pyngrok import ngrok

            webhook_url = ngrok.connect(port, "http").public_url + path
        else:
            webhook_url = telegram_config.webhook_url()

        async with aiohttp.ClientSession() as session:
            client = TelegramClient(session, telegram_config.bot_token())
            await client.set_webhook(webhook_url, secret_token)

            app = create_app(agent, client, telegram_config, secret_token)
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", port)
            await site.start()
            print(f"Listening on 0.0.0.0:{port}{path}")
            if args.ngrok:
                print(f"Public URL: {webhook_url}")
            await asyncio.Event().wait()


def main() -> None:
    asyncio.run(amain())
