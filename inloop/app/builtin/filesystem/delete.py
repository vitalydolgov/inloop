"""Built-in filesystem tool for deleting a local file or directory."""

from inloop.app.filesystem import FileSystem
from inloop.domain.tool import Tool
from inloop_kit.tool import tool

DESCRIPTION = (
    "Deletes a file or directory from the local filesystem. "
    "Use when the user explicitly asks to remove a path; set `recursive` to true only when deleting "
    "a directory and its contents. "
    "It refuses non-empty directories unless recursive deletion is requested and cannot be undone."
)

PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path of the file or directory to delete.",
        },
        "recursive": {
            "type": "boolean",
            "description": "Delete a directory and all its contents. Defaults to false.",
        },
    },
    "required": ["path"],
}


def delete_tool(fs: FileSystem) -> Tool:
    """Return a delete tool that removes paths through the given filesystem."""

    @tool(name="delete", description=DESCRIPTION, parameters=PARAMETERS)
    def delete(args: dict[str, object]) -> str:
        path = str(args["path"])
        recursive = bool(args.get("recursive", False))
        try:
            fs.delete(path, recursive)
        except OSError as error:
            return f"Error: could not delete {path}: {error}"
        return f"Deleted {path}"

    return delete
