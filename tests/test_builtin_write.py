"""Tests for the built-in write tool."""

import asyncio

from inloop.app.builtin import write


class _FakeFileSystem:
    """A FileSystem holding file contents in an in-memory mapping."""

    def __init__(self, files: dict[str, str] | None = None) -> None:
        self.files = dict(files or {})

    def read_text(self, path: str) -> str:
        if path not in self.files:
            raise FileNotFoundError(f"No such file: {path}")
        return self.files[path]

    def write_text(self, path: str, content: str) -> None:
        self.files[path] = content


class _ReadOnlyFileSystem:
    """A FileSystem that refuses every write."""

    def read_text(self, path: str) -> str:
        raise FileNotFoundError(path)

    def write_text(self, path: str, content: str) -> None:
        raise PermissionError("read-only")


def _write(fs, args: dict[str, object]) -> str:
    return asyncio.run(write.write_tool(fs).execute(args))


def test_creates_a_new_file() -> None:
    fs = _FakeFileSystem()

    out = _write(fs, {"path": "a.txt", "content": "hello\nworld"})

    assert fs.files["a.txt"] == "hello\nworld"
    assert out == "Wrote 2 lines to a.txt"


def test_overwrites_an_existing_file() -> None:
    fs = _FakeFileSystem({"a.txt": "old contents"})

    _write(fs, {"path": "a.txt", "content": "new"})

    assert fs.files["a.txt"] == "new"


def test_write_failure_returns_an_error_message() -> None:
    out = _write(_ReadOnlyFileSystem(), {"path": "a.txt", "content": "x"})

    assert out.startswith("Error: could not write a.txt")


def test_tool_is_named_write() -> None:
    assert write.write_tool(_FakeFileSystem()).name == "write"
