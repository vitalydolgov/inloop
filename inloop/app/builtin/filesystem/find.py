"""Built-in filesystem tool for finding files by name."""

from inloop.app.filesystem import FileSystem
from inloop.domain.tool import Tool
from inloop_kit.tool import tool

DESCRIPTION = (
    "Finds files below a directory whose names match a glob pattern, returning one path per line. "
    "Use when you need to locate a file by name or extension, such as finding every `*.py` file or "
    "a file named `README.md`. "
    "It searches file names recursively but does not search file contents or modify the filesystem."
)

PARAMETERS = {
    "type": "object",
    "properties": {
        "pattern": {
            "type": "string",
            "description": "Glob pattern for file names, such as `*.py` or `README.md`.",
        },
        "path": {
            "type": "string",
            "description": "Directory under which to search. Defaults to the current directory.",
        },
    },
    "required": ["pattern"],
}


def find_tool(fs: FileSystem) -> Tool:
    """Return a find tool that locates files through the given filesystem."""

    @tool(name="find", description=DESCRIPTION, parameters=PARAMETERS)
    def find(args: dict[str, object]) -> str:
        pattern = str(args["pattern"])
        path = str(args.get("path") or ".")
        if not pattern:
            return "Error: `pattern` must not be empty"
        try:
            matches = sorted(fs.find(path, pattern))
        except OSError as error:
            return f"Error: could not find files under {path}: {error}"
        return "\n".join(matches) if matches else "No files found"

    return find
