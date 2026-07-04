"""Built-in tool for patching a file by replacing an exact span of text."""

from inloop.app.filesystem import FileSystem
from inloop.domain.tool import Tool
from inloop_kit.tool import tool

DESCRIPTION = (
    "Patches an existing file by replacing one exact occurrence of a text span with new text. "
    "Use for targeted edits to a file you have already read — fixing a line, renaming a symbol, "
    "inserting or removing a passage — without rewriting the whole file. "
    "The `old` text must match exactly and occur exactly once, or the patch is refused; to create a "
    "file or replace it in full, prefer `write`."
)

PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to the file to patch.",
        },
        "old": {
            "type": "string",
            "description": "The exact text to find; must occur exactly once in the file.",
        },
        "new": {
            "type": "string",
            "description": "The text to replace it with. Use an empty string to delete the old text.",
        },
    },
    "required": ["path", "old", "new"],
}


def patch_tool(fs: FileSystem) -> Tool:
    """Return a Patch tool that applies targeted text replacements through the given filesystem."""

    @tool(name="patch", description=DESCRIPTION, parameters=PARAMETERS)
    def patch(args: dict[str, object]) -> str:
        path = args["path"]
        old = args["old"]
        new = args["new"]
        if not old:
            return "Error: `old` must not be empty"
        try:
            text = fs.read_text(path)
        except OSError as error:
            return f"Error: could not read {path}: {error}"
        count = text.count(old)
        if count == 0:
            return f"Error: `old` text not found in {path}"
        if count > 1:
            return f"Error: `old` text occurs {count} times in {path}; add surrounding context to make it unique"
        try:
            fs.write_text(path, text.replace(old, new))
        except OSError as error:
            return f"Error: could not write {path}: {error}"
        return f"Patched {path}"

    return patch
