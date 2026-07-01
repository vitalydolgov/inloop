"""Run a single tool from an installed extension, without starting the agent."""

import sys

from inloop.domain.extension import Extension
from inloop.infra.directory_registry import DirectoryExtensionRegistry
from inloop.infra.env_config import EnvConfig


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


def _run(extension: Extension, tool_name: str, pairs: list[str]) -> str:
    """Execute one of an extension's tools by name with key=value pairs. Raises KeyError for unknown tools."""
    tools = {t.name: t for t in extension.tools}
    if tool_name not in tools:
        raise KeyError(f"Unknown tool {tool_name!r}")
    return tools[tool_name].execute(_parse_args(pairs))


def main() -> None:
    """Run the extension tool-testing command."""
    if len(sys.argv) < 3:
        print("Usage: probe <extension> <tool_name> [key=value ...]", file=sys.stderr)
        sys.exit(1)
    extension_name, tool_name, *pairs = sys.argv[1:]

    config = EnvConfig()
    registry = DirectoryExtensionRegistry(config.extensions_path())
    extensions = {ext.name: ext for ext in registry.load()}

    if extension_name not in extensions:
        print(f"Unknown extension {extension_name!r}", file=sys.stderr)
        sys.exit(1)

    try:
        print(_run(extensions[extension_name], tool_name, pairs))
    except KeyError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
