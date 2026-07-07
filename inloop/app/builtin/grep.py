"""Built-in tool for searching file contents by regular expression."""

import re

from inloop.app.search import Search
from inloop.domain.tool import Tool
from inloop_kit.tool import tool

MATCH_LIMIT = 100

DESCRIPTION = (
    "Searches file contents for a regular expression across a directory tree, returning each "
    "matching line as `path:line:text`. "
    "Use to find where a symbol, string, or pattern appears — locating a definition, its callers, "
    "or every TODO — when you do not already know which file to open. "
    "Matches file contents, not file names, and never edits; read a match in context with `read`, "
    "and narrow `pattern` or `glob` if the results are capped."
)

PARAMETERS = {
    "type": "object",
    "properties": {
        "pattern": {
            "type": "string",
            "description": "The regular expression to search for, matched against each line.",
        },
        "path": {
            "type": "string",
            "description": "File or directory to search under. Defaults to the current directory.",
        },
        "glob": {
            "type": "string",
            "description": "Restrict the search to files whose name matches this glob, such as `*.py`.",
        },
    },
    "required": ["pattern"],
}


def grep_tool(search: Search) -> Tool:
    """Return a Grep tool that searches file contents through the given search port."""

    @tool(name="grep", description=DESCRIPTION, parameters=PARAMETERS)
    def grep(args: dict[str, object]) -> str:
        pattern = args["pattern"]
        path = args.get("path") or "."
        glob = args.get("glob")
        try:
            re.compile(pattern)
        except re.error as error:
            return f"Error: invalid pattern: {error}"
        try:
            matches = search.search(pattern, path, glob)
        except OSError as error:
            return f"Error: could not search {path}: {error}"
        if not matches:
            return "No matches found"
        lines = [f"{m.path}:{m.line}:{m.text}" for m in matches[:MATCH_LIMIT]]
        if len(matches) > MATCH_LIMIT:
            lines.append(f"... ({len(matches) - MATCH_LIMIT} more matches)")
        return "\n".join(lines)

    return grep
