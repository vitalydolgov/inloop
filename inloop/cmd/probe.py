"""Run a single tool from an installed extension, without starting the agent."""

import asyncio
import sys

from inloop.infra import app_dirs
from inloop.infra.directory_registry import DirectoryExtensionRegistry


def _is_bool(val: str) -> bool:
    return val.lower() in ("true", "false")


def _is_int(val: str) -> bool:
    try:
        int(val)
        return True
    except ValueError:
        return False


def _parse_args(pairs: list[str]) -> dict[str, object]:
    args: dict[str, object] = {}
    for pair in pairs:
        key, _, val = pair.partition("=")
        if _is_bool(val):
            args[key] = val.lower() == "true"
        elif _is_int(val):
            args[key] = int(val)
        else:
            args[key] = val
    return args


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: probe <extension> <tool_name> [key=value ...]", file=sys.stderr)
        sys.exit(1)
    extension_name, tool_name, *pairs = sys.argv[1:]

    registry = DirectoryExtensionRegistry(app_dirs.extensions_dir())
    extensions = {ext.name: ext for ext in registry.load()}

    if extension_name not in extensions:
        print(f"Unknown extension {extension_name!r}", file=sys.stderr)
        sys.exit(1)

    tools = {t.name: t for t in extensions[extension_name].tools}
    if tool_name not in tools:
        print(f"Unknown tool {tool_name!r}", file=sys.stderr)
        sys.exit(1)

    args = _parse_args(pairs)
    result = asyncio.run(tools[tool_name].execute(args))
    print(result)
