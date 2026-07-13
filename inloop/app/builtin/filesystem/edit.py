"""Built-in filesystem tool for editing a file by replacing an exact text span."""

from inloop.app.filesystem import FileSystem
from inloop.domain.tool import Tool
from inloop_kit.tool import tool

DESCRIPTION = (
    "Edits an existing local file by replacing one exact occurrence of a text span with new text. "
    "Use for targeted changes after reading a file, such as fixing a line, renaming a symbol, or "
    "inserting or removing a passage. "
    "The old text must occur exactly once and the tool does not create files; use `write` to create "
    "a file or replace its entire contents."
)

PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to the file to edit.",
        },
        "old": {
            "type": "string",
            "description": "The exact text to replace. It must occur exactly once in the file.",
        },
        "new": {
            "type": "string",
            "description": "Replacement text. Use an empty string to delete the old text.",
        },
    },
    "required": ["path", "old", "new"],
}


def edit_tool(fs: FileSystem) -> Tool:
    """Return an edit tool that applies one exact replacement through the given filesystem."""

    @tool(name="edit", description=DESCRIPTION, parameters=PARAMETERS)
    def edit(args: dict[str, object]) -> str:
        path = str(args["path"])
        old = str(args["old"])
        new = str(args["new"])
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
        return f"Edited {path}"

    return edit
