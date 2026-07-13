"""Tests for the built-in filesystem edit tool."""

import asyncio

from inloop.app.builtin.filesystem import edit


class _FakeFileSystem:
    """A FileSystem holding file contents in an in-memory mapping."""

    def __init__(self, files: dict[str, str] | None = None) -> None:
        self.files = dict(files or {})

    def read_text(self, path: str) -> str:
        if path not in self.files:
            raise FileNotFoundError(f"No such file: {path}")
        return self.files[path]

    def write_text(self, path: str, content: str):
        self.files[path] = content


class _ReadOnlyFileSystem:
    """A FileSystem that refuses every write."""

    def read_text(self, path: str) -> str:
        return "hello"

    def write_text(self, path: str, content: str):
        raise PermissionError("read-only")


def _edit(fs, args: dict[str, object]) -> str:
    return asyncio.run(edit.edit_tool(fs).execute(args))


def test_replaces_a_unique_occurrence() -> None:
    fs = _FakeFileSystem({"a.txt": "one\ntwo\nthree"})

    out = _edit(fs, {"path": "a.txt", "old": "two", "new": "TWO"})

    assert fs.files["a.txt"] == "one\nTWO\nthree"
    assert out == "Edited a.txt"


def test_empty_new_deletes_the_old_text() -> None:
    fs = _FakeFileSystem({"a.txt": "keep this away"})

    _edit(fs, {"path": "a.txt", "old": " away", "new": ""})

    assert fs.files["a.txt"] == "keep this"


def test_missing_old_text_is_refused_without_writing() -> None:
    fs = _FakeFileSystem({"a.txt": "hello"})

    out = _edit(fs, {"path": "a.txt", "old": "absent", "new": "x"})

    assert out == "Error: `old` text not found in a.txt"
    assert fs.files["a.txt"] == "hello"


def test_ambiguous_old_text_is_refused_without_writing() -> None:
    fs = _FakeFileSystem({"a.txt": "ab ab ab"})

    out = _edit(fs, {"path": "a.txt", "old": "ab", "new": "cd"})

    assert out == "Error: `old` text occurs 3 times in a.txt; add surrounding context to make it unique"
    assert fs.files["a.txt"] == "ab ab ab"


def test_empty_old_text_is_refused() -> None:
    fs = _FakeFileSystem({"a.txt": "hello"})

    out = _edit(fs, {"path": "a.txt", "old": "", "new": "x"})

    assert out == "Error: `old` must not be empty"


def test_missing_file_returns_an_error_message() -> None:
    out = _edit(_FakeFileSystem(), {"path": "gone.txt", "old": "a", "new": "b"})

    assert out.startswith("Error: could not read gone.txt")


def test_write_failure_returns_an_error_message() -> None:
    out = _edit(_ReadOnlyFileSystem(), {"path": "a.txt", "old": "hello", "new": "goodbye"})

    assert out.startswith("Error: could not write a.txt")


def test_tool_is_named_edit() -> None:
    assert edit.edit_tool(_FakeFileSystem()).name == "edit"
