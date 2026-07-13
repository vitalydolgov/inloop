"""Built-in filesystem tool for writing a whole local file."""

from inloop.app.filesystem import FileSystem
from inloop.domain.tool import Tool
from inloop_kit.tool import tool

DESCRIPTION = (
    "Writes text to a file on the local filesystem, creating it or replacing its entire contents. "
    "Use when the user wants to create a new file, or to overwrite an existing one wholesale with "
    "known contents. "
    "Always replaces the whole file and does not create missing parent directories; use `read` first "
    "when you need to preserve or inspect existing content."
)

PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to the file to write.",
        },
        "content": {
            "type": "string",
            "description": "The full text content to write to the file.",
        },
    },
    "required": ["path", "content"],
}


def write_tool(fs: FileSystem) -> Tool:
    """Return a write tool that writes whole files through the given filesystem."""

    @tool(name="write", description=DESCRIPTION, parameters=PARAMETERS)
    def write(args: dict[str, object]) -> str:
        path = str(args["path"])
        content = str(args["content"])
        try:
            fs.write_text(path, content)
        except OSError as error:
            return f"Error: could not write {path}: {error}"
        return f"Wrote {len(content.splitlines())} lines to {path}"

    return write
