"""Filesystem extension — read, write, and patch files."""

from domain import extension
from domain import tool

from filesystem import operations


def _run(fn, *args):
    try:
        result = fn(*args)
        return "ok" if result is None else result
    except Exception as exc:
        return str(exc)


read = tool.Tool(
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
    execute=lambda args: _run(operations.read, str(args["path"])),
)

write = tool.Tool(
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
    execute=lambda args: _run(operations.write, str(args["path"]), str(args["content"])),
)

patch = tool.Tool(
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
    execute=lambda args: _run(operations.patch, str(args["path"]), str(args["old"]), str(args["new"])),
)

EXTENSION = extension.Extension(name="filesystem", tools=[read, write, patch])
