"""Run a short conversation, streaming each reply as it arrives."""

import sys

import anthropic

from app import conversation
from domain import streaming
from infra import anthropic_model


def main() -> None:
    """Send each command-line argument (or stdin line) as a subsequent user message."""
    messages = [arg.strip() for arg in sys.argv[1:] if arg.strip()]
    if not messages:
        messages = [line.strip() for line in sys.stdin if line.strip()]
    if not messages:
        print("usage: demo <message> [message ...]", file=sys.stderr)
        raise SystemExit(1)

    chat = conversation.Conversation(anthropic_model.AnthropicModel(anthropic.Anthropic()))
    for text in messages:
        print(f"> {text}")
        for event in chat.ask(text):
            match event:
                case streaming.TextDelta(delta):
                    print(delta, end="", flush=True)
                case streaming.MessageCompleted(_, stop_reason):
                    print(f"\n[done: {stop_reason}]\n")
