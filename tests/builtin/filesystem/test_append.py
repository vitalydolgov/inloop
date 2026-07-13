"""Tests for the built-in filesystem append tool."""

import asyncio

from inloop.app.builtin.filesystem import append


class _FakeFileSystem:
    """A FileSystem holding file contents in an in-memory mapping."""

    def __init__(self, files: dict[str, str] | None = None) -> None:
        self.files = dict(files or {})

    def append_text(self, path: str, content: str):
        self.files[path] = self.files.get(path, "") + content


class _ReadOnlyFileSystem:
    """A FileSystem that refuses every append."""

    def append_text(self, path: str, content: str):
        raise PermissionError("read-only")


def _append(fs, args: dict[str, object]) -> str:
    return asyncio.run(append.append_tool(fs).execute(args))


def test_appends_to_an_existing_file() -> None:
    fs = _FakeFileSystem({"a.txt": "hello\n"})

    out = _append(fs, {"path": "a.txt", "content": "world\nagain"})

    assert fs.files["a.txt"] == "hello\nworld\nagain"
    assert out == "Appended 2 lines to a.txt"


def test_creates_a_missing_file() -> None:
    fs = _FakeFileSystem()

    _append(fs, {"path": "a.txt", "content": "new"})

    assert fs.files["a.txt"] == "new"


def test_append_failure_returns_an_error_message() -> None:
    out = _append(_ReadOnlyFileSystem(), {"path": "a.txt", "content": "x"})

    assert out.startswith("Error: could not append to a.txt")


def test_tool_is_named_append() -> None:
    assert append.append_tool(_FakeFileSystem()).name == "append"
