"""Tests for the built-in patch tool."""

import asyncio

from inloop.app.builtin import patch


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


def _patch(fs, args: dict[str, object]) -> str:
    return asyncio.run(patch.patch_tool(fs).execute(args))


def test_replaces_a_unique_occurrence() -> None:
    fs = _FakeFileSystem({"a.txt": "one\ntwo\nthree"})

    out = _patch(fs, {"path": "a.txt", "old": "two", "new": "TWO"})

    assert fs.files["a.txt"] == "one\nTWO\nthree"
    assert out == "Patched a.txt"


def test_empty_new_deletes_the_old_text() -> None:
    fs = _FakeFileSystem({"a.txt": "keep this away"})

    _patch(fs, {"path": "a.txt", "old": " away", "new": ""})

    assert fs.files["a.txt"] == "keep this"


def test_missing_old_text_is_refused() -> None:
    fs = _FakeFileSystem({"a.txt": "hello"})

    out = _patch(fs, {"path": "a.txt", "old": "absent", "new": "x"})

    assert out == "Error: `old` text not found in a.txt"
    assert fs.files["a.txt"] == "hello"


def test_ambiguous_old_text_is_refused() -> None:
    fs = _FakeFileSystem({"a.txt": "ab ab ab"})

    out = _patch(fs, {"path": "a.txt", "old": "ab", "new": "cd"})

    assert out == "Error: `old` text occurs 3 times in a.txt; add surrounding context to make it unique"
    assert fs.files["a.txt"] == "ab ab ab"


def test_empty_old_is_refused() -> None:
    fs = _FakeFileSystem({"a.txt": "hello"})

    out = _patch(fs, {"path": "a.txt", "old": "", "new": "x"})

    assert out == "Error: `old` must not be empty"


def test_missing_file_returns_an_error_message() -> None:
    out = _patch(_FakeFileSystem(), {"path": "gone.txt", "old": "a", "new": "b"})

    assert out.startswith("Error: could not read gone.txt")


def test_tool_is_named_patch() -> None:
    assert patch.patch_tool(_FakeFileSystem()).name == "patch"
