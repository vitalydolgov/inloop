"""Run a single tool from an installed extension, without starting the agent."""

import asyncio
import gc
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


async def _wait_for_subprocesses(timeout: float = 3) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        processes = [
            obj
            for obj in gc.get_objects()
            if isinstance(obj, asyncio.subprocess.Process) and obj.returncode is None
        ]
        if not processes:
            break
        if loop.time() >= deadline:
            break
        await asyncio.sleep(0.05)


async def _execute_tool(tool, args: dict[str, object]) -> str:
    result = await tool.execute(args)
    pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    if pending:
        try:
            await asyncio.wait_for(
                asyncio.gather(*pending, return_exceptions=True), timeout=3
            )
        except asyncio.TimeoutError:
            pass
    return result


async def amain() -> None:
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
    result = await _execute_tool(tools[tool_name], args)
    await _wait_for_subprocesses()
    print(result)


def main() -> None:
    asyncio.run(amain())
