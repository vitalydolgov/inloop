"""Built-in filesystem tool for creating a local directory."""

from inloop.app.filesystem import FileSystem
from inloop.domain.tool import Tool
from inloop_kit.tool import tool

DESCRIPTION = (
    "Creates a directory on the local filesystem, optionally creating missing parent directories. "
    "Use when the user asks to create a directory or when a destination directory is needed before "
    "writing or moving a file. "
    "It refuses to replace an existing path and does not create files."
)

PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Directory path to create.",
        },
        "parents": {
            "type": "boolean",
            "description": "Create missing parent directories as needed. Defaults to false.",
        },
    },
    "required": ["path"],
}


def mkdir_tool(fs: FileSystem) -> Tool:
    """Return a mkdir tool that creates directories through the given filesystem."""

    @tool(name="mkdir", description=DESCRIPTION, parameters=PARAMETERS)
    def mkdir(args: dict[str, object]) -> str:
        path = str(args["path"])
        parents = bool(args.get("parents", False))
        try:
            fs.make_dir(path, parents)
        except OSError as error:
            return f"Error: could not create directory {path}: {error}"
        return f"Created directory {path}"

    return mkdir
