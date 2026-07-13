"""Tests for the built-in filesystem copy tool."""

import asyncio

from inloop.app.builtin.filesystem import copy


class _FakeFileSystem:
    """A FileSystem recording paths copied through it."""

    def __init__(self) -> None:
        self.copies: list[tuple[str, str, bool]] = []

    def copy(self, source: str, destination: str, recursive: bool):
        self.copies.append((source, destination, recursive))


class _FailingFileSystem:
    """A FileSystem that refuses to copy paths."""

    def copy(self, source: str, destination: str, recursive: bool):
        raise FileExistsError(destination)


def _copy(fs, args: dict[str, object]) -> str:
    return asyncio.run(copy.copy_tool(fs).execute(args))


def test_copies_a_file_without_recursion_by_default() -> None:
    fs = _FakeFileSystem()

    out = _copy(fs, {"source": "old.txt", "destination": "new.txt"})

    assert fs.copies == [("old.txt", "new.txt", False)]
    assert out == "Copied old.txt to new.txt"


def test_can_copy_a_directory_recursively() -> None:
    fs = _FakeFileSystem()

    _copy(fs, {"source": "src", "destination": "backup", "recursive": True})

    assert fs.copies == [("src", "backup", True)]


def test_copy_failure_returns_an_error_message() -> None:
    out = _copy(
        _FailingFileSystem(),
        {"source": "old.txt", "destination": "new.txt"},
    )

    assert out.startswith("Error: could not copy old.txt to new.txt")


def test_tool_is_named_copy() -> None:
    assert copy.copy_tool(_FakeFileSystem()).name == "copy"
