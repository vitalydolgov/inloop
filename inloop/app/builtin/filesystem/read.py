"""Built-in filesystem tool for reading a local file or a portion of it."""

from inloop.app.filesystem import FileSystem
from inloop.domain.tool import Tool
from inloop_kit.tool import tool

DESCRIPTION = (
    "Reads a file from the local filesystem and returns its contents as numbered lines. "
    "Use when the user wants to view, inspect, or quote a specific file, or when you need a "
    "file's exact contents before acting on it; pass `offset` and `limit` to read only a "
    "portion of a large file. "
    "Reads a single local file only — it does not list directories, search across files, or "
    "fetch remote URLs; output is line-numbered text, so an empty result means the file or the "
    "requested range is empty."
)

PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to the file to read.",
        },
        "offset": {
            "type": "integer",
            "description": "1-based line number to start reading from. Omit to start at the first line.",
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of lines to read. Omit to read through the end of the file.",
        },
    },
    "required": ["path"],
}


def read_tool(fs: FileSystem) -> Tool:
    """Return a read tool that serves file contents through the given filesystem."""

    @tool(name="read", description=DESCRIPTION, parameters=PARAMETERS)
    def read(args: dict[str, object]) -> str:
        path = str(args["path"])
        offset = args.get("offset")
        limit = args.get("limit")
        try:
            text = fs.read_text(path)
        except OSError as error:
            return f"Error: could not read {path}: {error}"
        lines = text.splitlines()
        start = max((offset or 1) - 1, 0)
        end = start + limit if limit is not None else len(lines)
        window = lines[start:end]
        if not window:
            if not lines:
                return f"{path} is empty"
            return f"{path} has no lines in the requested range"
        return "\n".join(f"{start + n:6d}\t{line}" for n, line in enumerate(window, start=1))

    return read
