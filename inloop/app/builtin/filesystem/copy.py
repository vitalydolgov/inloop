"""Built-in filesystem tool for copying a local file or directory."""

from inloop.app.filesystem import FileSystem
from inloop.domain.tool import Tool
from inloop_kit.tool import tool

DESCRIPTION = (
    "Copies a local file or directory to a new destination path. "
    "Use when the user wants to duplicate a file or directory; set `recursive` to true when copying "
    "a directory and its contents. "
    "The destination must not already exist, and the tool does not create missing parent directories."
)

PARAMETERS = {
    "type": "object",
    "properties": {
        "source": {
            "type": "string",
            "description": "Path of the file or directory to copy.",
        },
        "destination": {
            "type": "string",
            "description": "New path for the copied file or directory.",
        },
        "recursive": {
            "type": "boolean",
            "description": "Copy a directory and all its contents. Defaults to false.",
        },
    },
    "required": ["source", "destination"],
}


def copy_tool(fs: FileSystem) -> Tool:
    """Return a copy tool that copies paths through the given filesystem."""

    @tool(name="copy", description=DESCRIPTION, parameters=PARAMETERS)
    def copy(args: dict[str, object]) -> str:
        source = str(args["source"])
        destination = str(args["destination"])
        recursive = bool(args.get("recursive", False))
        try:
            fs.copy(source, destination, recursive)
        except OSError as error:
            return f"Error: could not copy {source} to {destination}: {error}"
        return f"Copied {source} to {destination}"

    return copy
