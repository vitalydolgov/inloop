"""Built-in filesystem tool for moving a local file or directory."""

from inloop.app.filesystem import FileSystem
from inloop.domain.tool import Tool
from inloop_kit.tool import tool

DESCRIPTION = (
    "Moves a local file or directory to a new destination path. "
    "Use when the user wants to rename or relocate a file or directory. "
    "The destination must not already exist, and the tool does not create missing parent directories."
)

PARAMETERS = {
    "type": "object",
    "properties": {
        "source": {
            "type": "string",
            "description": "Path of the file or directory to move.",
        },
        "destination": {
            "type": "string",
            "description": "New path for the file or directory.",
        },
    },
    "required": ["source", "destination"],
}


def move_tool(fs: FileSystem) -> Tool:
    """Return a move tool that moves paths through the given filesystem."""

    @tool(name="move", description=DESCRIPTION, parameters=PARAMETERS)
    def move(args: dict[str, object]) -> str:
        source = str(args["source"])
        destination = str(args["destination"])
        try:
            fs.move(source, destination)
        except OSError as error:
            return f"Error: could not move {source} to {destination}: {error}"
        return f"Moved {source} to {destination}"

    return move
