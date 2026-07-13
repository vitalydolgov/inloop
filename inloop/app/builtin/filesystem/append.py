"""Built-in filesystem tool for appending text to a local file."""

from inloop.app.filesystem import FileSystem
from inloop.domain.tool import Tool
from inloop_kit.tool import tool

DESCRIPTION = (
    "Appends text to a file on the local filesystem, creating the file when it does not exist. "
    "Use when new content belongs at the end of an existing file without replacing its current "
    "contents. Parent directories must already exist; use `mkdir` first when necessary."
)

PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to the file to append.",
        },
        "content": {
            "type": "string",
            "description": "Text to add at the end of the file.",
        },
    },
    "required": ["path", "content"],
}


def append_tool(fs: FileSystem) -> Tool:
    """Return an append tool that adds text through the given filesystem."""

    @tool(name="append", description=DESCRIPTION, parameters=PARAMETERS)
    def append(args: dict[str, object]) -> str:
        path = str(args["path"])
        content = str(args["content"])
        try:
            fs.append_text(path, content)
        except OSError as error:
            return f"Error: could not append to {path}: {error}"
        return f"Appended {len(content.splitlines())} lines to {path}"

    return append
