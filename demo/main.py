"""Stream a single message to the model and print the response as it arrives."""

import sys

import anthropic

from app import conversation
from domain import streaming
from infra import anthropic_model


def main() -> None:
    """Read a message from the command line (or stdin) and stream the reply."""
    message = " ".join(sys.argv[1:]).strip() or sys.stdin.read().strip()
    if not message:
        print("usage: demo <message>", file=sys.stderr)
        raise SystemExit(1)

    model = anthropic_model.AnthropicModel(anthropic.Anthropic())
    for event in conversation.ask(model, message):
        match event:
            case streaming.TextDelta(text):
                print(text, end="", flush=True)
            case streaming.MessageCompleted(_, stop_reason):
                print(f"\n[done: {stop_reason}]")
