"""Filesystem extension: read, write, and patch files."""

from pathlib import Path

from inloop import contrib


@contrib.tool(
    name="read",
    description=(
        "Read and return the full text content of a file given its path. "
        "Use when the user wants to view, inspect, or reference a file's contents. "
        "Returns the raw text; does not interpret or summarize it."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative path to the file."},
        },
        "required": ["path"],
    },
)
def read(args: dict[str, object]) -> str:
    return Path(str(args["path"])).expanduser().read_text()


@contrib.tool(
    name="write",
    description=(
        "Write text content to a file, creating the file and any missing parent directories. "
        "Use when the user wants to create or fully overwrite a file. "
        "Does not append — replaces the entire file; use patch to change part of a file."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative path to the file."},
            "content": {"type": "string", "description": "Text content to write."},
        },
        "required": ["path", "content"],
    },
)
def write(args: dict[str, object]) -> None:
    p = Path(str(args["path"])).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(str(args["content"]))


@contrib.tool(
    name="patch",
    description=(
        "Replace the first occurrence of a string in a file with new text. "
        "Use for targeted edits when only part of a file needs to change. "
        "Returns an error if the original string is not found; use write to replace the whole file."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative path to the file."},
            "old": {"type": "string", "description": "The text to find and replace."},
            "new": {"type": "string", "description": "The replacement text."},
        },
        "required": ["path", "old", "new"],
    },
)
def patch(args: dict[str, object]) -> None:
    p = Path(str(args["path"])).expanduser()
    text = p.read_text()
    old = str(args["old"])
    if old not in text:
        raise ValueError(f"text not found: {old!r}")
    p.write_text(text.replace(old, str(args["new"]), 1))


EXTENSION = contrib.Extension(name="filesystem", tools=[read, write, patch])
