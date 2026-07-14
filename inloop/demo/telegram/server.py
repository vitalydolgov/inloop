"""aiohttp application that serves Telegram webhook updates to the agent."""

import html
import json
from collections.abc import AsyncIterator

from aiohttp import web

from inloop.app.agent import Agent
from inloop.domain import streaming
from inloop.demo.telegram import formatting
from inloop.demo.telegram.client import TelegramClient
from inloop.demo.telegram.config import TelegramConfig

SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"
MESSAGE_LIMIT = 4096


def create_app(
    agent: Agent, client: TelegramClient, config: TelegramConfig, secret_token: str
) -> web.Application:
    """Build the aiohttp application that receives updates for one Telegram bot."""

    async def handle_update(request: web.Request) -> web.Response:
        if request.headers.get(SECRET_HEADER) != secret_token:
            return web.Response(status=403)

        update = await request.json()
        incoming = update.get("message", {})
        text = incoming.get("text")
        chat_id = incoming.get("chat", {}).get("id")

        if text:
            await _reply(agent, client, chat_id, text)

        return web.Response()

    app = web.Application()
    app.router.add_post(config.webhook_path(), handle_update)
    return app


async def _single_message(text: str) -> AsyncIterator[str]:
    yield text


def _chunks(html_text: str) -> list[str]:
    return [html_text[i : i + MESSAGE_LIMIT] for i in range(0, len(html_text), MESSAGE_LIMIT)]


async def _reply(agent: Agent, client: TelegramClient, chat_id: int, text: str) -> None:
    async for event in agent.events(_single_message(text)):
        match event:
            case streaming.ToolUse(_, name, input):
                name = name.replace('__', ':', 1)
                arguments = html.escape(json.dumps(input, ensure_ascii=False, indent=2))
                await client.send_message(
                    chat_id,
                    f"⛭ {html.escape(name)}\n{arguments}",
                )
            case streaming.Compaction.ENDED:
                await client.send_message(chat_id, "\u2723 compacted")
            case streaming.MessageCompleted(reply_text, _) if reply_text:
                for chunk in _chunks(formatting.to_telegram_html(reply_text)):
                    await client.send_message(chat_id, chunk)
            case streaming.Failed(error):
                await client.send_message(chat_id, f"⨯ error: {html.escape(error)}")
