"""Dispatch subcommands to the appropriate inloop entry point."""

import sys
from typing import Callable


_Command = Callable[[], None]


def _run(name: str, command: _Command, args: list[str]):
    original = sys.argv
    sys.argv = [name, *args]
    try:
        command()
    finally:
        sys.argv = original


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
        from inloop.demo import main as demo

        _run("inloop", demo.main, sys.argv[1:])
        return

    command, *args = sys.argv[1:]

    match command:
        case "telegram-demo":
            from inloop.demo.telegram import main as telegram_demo

            _run("telegram-demo", telegram_demo.main, args)
        case _:
            print(f"Unknown command: {command}", file=sys.stderr)
            print("Usage: inloop [telegram-demo]", file=sys.stderr)
            sys.exit(1)
