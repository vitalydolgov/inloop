"""Tests for the built-in filesystem delete tool."""

import asyncio

from inloop.app.builtin.filesystem import delete


class _FakeFileSystem:
    """A FileSystem recording paths deleted through it."""

    def __init__(self) -> None:
        self.deleted: list[tuple[str, bool]] = []

    def delete(self, path: str, recursive: bool):
        self.deleted.append((path, recursive))


class _FailingFileSystem:
    """A FileSystem that refuses to delete paths."""

    def delete(self, path: str, recursive: bool):
        raise OSError("directory is not empty")


def _delete(fs, args: dict[str, object]) -> str:
    return asyncio.run(delete.delete_tool(fs).execute(args))


def test_deletes_a_path_without_recursion_by_default() -> None:
    fs = _FakeFileSystem()

    out = _delete(fs, {"path": "old.txt"})

    assert fs.deleted == [("old.txt", False)]
    assert out == "Deleted old.txt"


def test_can_delete_recursively() -> None:
    fs = _FakeFileSystem()

    _delete(fs, {"path": "build", "recursive": True})

    assert fs.deleted == [("build", True)]


def test_delete_failure_returns_an_error_message() -> None:
    out = _delete(_FailingFileSystem(), {"path": "build"})

    assert out.startswith("Error: could not delete build")


def test_tool_is_named_delete() -> None:
    assert delete.delete_tool(_FakeFileSystem()).name == "delete"
