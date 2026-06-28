"""Run an interactive chat, streaming each reply as it arrives."""

import argparse
import asyncio
import sys
from collections.abc import AsyncIterator

import anthropic

from app import conversation
from domain import streaming
from infra import anthropic_model


async def stdin_lines() -> AsyncIterator[str]:
    """Yield lines from stdin without blocking the event loop."""
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), sys.stdin)
    interactive = sys.stdin.isatty()
    while True:
        if interactive:
            print("> ", end="", flush=True)
        line = await reader.readline()
        if not line:
            break
        yield line.decode()


async def user_input(initial_message: str | None) -> AsyncIterator[str]:
    """Yield meaningful user messages for the chat."""
    if initial_message:
        yield initial_message

    async for line in stdin_lines():
        text = line.strip()
        if text:
            yield text


def stream_reply(chat: conversation.Conversation, text: str) -> None:
    """Stream one assistant reply for a user message."""
    for event in chat.ask(text):
        match event:
            case streaming.TextDelta(delta):
                print(delta, end="", flush=True)
            case streaming.MessageCompleted(_, stop_reason):
                print(f"\n[done: {stop_reason}]")


async def chat(initial_message: str | None) -> None:
    """Process the input stream indefinitely, streaming a reply for each message."""
    chat = conversation.Conversation(anthropic_model.AnthropicModel(anthropic.Anthropic()))
    async for text in user_input(initial_message):
        if text == "/exit":
            return
        stream_reply(chat, text)


def main() -> None:
    """Read requests from the terminal and stream each response."""
    argparse.ArgumentParser(prog="demo").parse_args()
    asyncio.run(chat(None))
