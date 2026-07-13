"""Run the Telegram bot, serving the agent over a webhook."""

import argparse
import asyncio
import hashlib
import os

import aiohttp
from aiohttp import web

from inloop.app.agent import Agent
from inloop.app.command import Command
from inloop.app.server_tools import ServerTools
from inloop.infra import app_dirs
from inloop.infra import toml_config
from inloop.infra.directory_registry import DirectoryExtensionRegistry
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

    config = toml_config.TomlConfig(app_dirs.config_path())
    async with ServerTools(config.mcp) as mcp_tools:
        registry = DirectoryExtensionRegistry(app_dirs.extensions_dir())
        agent = Agent(
            config.agent.model(),
            subagent_model=config.subagent.model(),
            extensions=registry.load(),
            server_tools=mcp_tools,
            commands=[
                Command("reload", "reconnect the configured tool servers", mcp_tools.reload),
            ],
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
