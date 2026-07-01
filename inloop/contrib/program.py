"""Library for building extension tool CLIs."""

import sys
from collections.abc import Callable

from inloop.domain.extension import Extension
from inloop.domain.tool import Tool


def _parse_args(pairs: list[str]) -> dict[str, object]:
    """Parse ['key=value', …] into a dict, auto-casting integers and booleans."""
    args: dict[str, object] = {}
    for pair in pairs:
        key, _, val = pair.partition("=")
        if val.lower() == "true":
            args[key] = True
        elif val.lower() == "false":
            args[key] = False
        else:
            try:
                args[key] = int(val)
            except ValueError:
                args[key] = val
    return args


def _run_tool(tools: dict[str, Tool], tool_name: str, pairs: list[str]) -> str:
    """Execute a tool by name with key=value pairs. Raises KeyError for unknown tools."""
    if tool_name not in tools:
        raise KeyError(f"Unknown tool {tool_name!r}")
    return tools[tool_name].execute(_parse_args(pairs))


def program(extension: Extension) -> Callable[[], None]:
    """Return a main() function for the given extension's tool CLI."""
    tools = {t.name: t for t in extension.tools}

    def main() -> None:
        argv = sys.argv[1:]
        if not argv:
            print(f"Usage: <tool_name> [key=value ...]", file=sys.stderr)
            sys.exit(1)
        try:
            print(_run_tool(tools, argv[0], argv[1:]))
        except KeyError as e:
            print(e, file=sys.stderr)
            sys.exit(1)
    return main
