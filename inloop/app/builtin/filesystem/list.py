"""Built-in filesystem tool for listing the contents of a local directory."""

from inloop.app.filesystem import FileSystem
from inloop.domain.tool import Tool
from inloop_kit.tool import tool

DESCRIPTION = (
    "Lists the entries in a local directory, one name per line in sorted order. "
    "Use when the user asks what files or directories are present, or when you need to discover "
    "the contents of a path before reading a file. "
    "It lists one directory only and does not read file contents, search recursively, or modify anything; "
    "pass a specific path when the current directory is not the target."
)

PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Directory to list. Defaults to the current directory.",
        },
    },
}


def list_tool(fs: FileSystem) -> Tool:
    """Return a list tool that lists directories through the given filesystem."""

    @tool(name="list", description=DESCRIPTION, parameters=PARAMETERS)
    def list(args: dict[str, object]) -> str:
        path = str(args.get("path") or ".")
        try:
            entries = sorted(fs.list(path))
        except OSError as error:
            return f"Error: could not list {path}: {error}"
        if not entries:
            return f"{path} is empty"
        return "\n".join(entries)

    return list
