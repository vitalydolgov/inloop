"""Built-in filesystem tool for searching one local text file."""

import re

from inloop.app.filesystem import FileSystem
from inloop.domain.tool import Tool
from inloop_kit.tool import tool

DESCRIPTION = (
    "Searches one local text file for a regular expression and returns matching lines with their "
    "1-based line numbers. "
    "Use when you need to find a symbol, string, or pattern in a file without reading the whole file. "
    "It searches one file only, does not search file names or directory trees, and never modifies the file."
)

PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to the text file to search.",
        },
        "pattern": {
            "type": "string",
            "description": "Regular expression to match against each line.",
        },
        "ignore_case": {
            "type": "boolean",
            "description": "Search without distinguishing uppercase and lowercase letters. Defaults to false.",
        },
    },
    "required": ["path", "pattern"],
}


def search_tool(fs: FileSystem) -> Tool:
    """Return a search tool that searches one text file through the given filesystem."""

    @tool(name="search", description=DESCRIPTION, parameters=PARAMETERS)
    def search(args: dict[str, object]) -> str:
        path = str(args["path"])
        pattern = str(args["pattern"])
        if not pattern:
            return "Error: `pattern` must not be empty"
        flags = re.IGNORECASE if args.get("ignore_case", False) else 0
        try:
            expression = re.compile(pattern, flags)
        except re.error as error:
            return f"Error: invalid pattern: {error}"
        try:
            text = fs.read_text(path)
        except (OSError, UnicodeError) as error:
            return f"Error: could not read {path}: {error}"
        matches = []
        for number, line in enumerate(text.splitlines(), start=1):
            if expression.search(line):
                matches.append(f"{number}: {line}")
        return "\n".join(matches) if matches else "No matches found"

    return search
