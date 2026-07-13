"""Tests for the built-in filesystem list tool."""

import asyncio

from inloop.app.builtin.filesystem import list as list_module


class _FakeFileSystem:
    """A FileSystem serving directory entries from an in-memory mapping."""

    def __init__(self, directories: dict[str, list[str]]) -> None:
        self._directories = directories

    def list(self, path: str) -> list[str]:
        if path not in self._directories:
            raise FileNotFoundError(f"No such directory: {path}")
        return self._directories[path]


def _list(directories: dict[str, list[str]], args: dict[str, object]) -> str:
    tool = list_module.list_tool(_FakeFileSystem(directories))
    return asyncio.run(tool.execute(args))


def test_lists_entries_in_sorted_order() -> None:
    out = _list({".": ["zeta.py", "alpha.py", "docs"]}, {})

    assert out == "alpha.py\ndocs\nzeta.py"


def test_lists_the_requested_directory() -> None:
    out = _list({"src": ["main.py", "test_main.py"]}, {"path": "src"})

    assert out == "main.py\ntest_main.py"


def test_missing_directory_returns_an_error_message() -> None:
    out = _list({}, {"path": "gone"})

    assert out.startswith("Error: could not list gone")


def test_empty_directory_reports_it_is_empty() -> None:
    out = _list({"empty": []}, {"path": "empty"})

    assert out == "empty is empty"


def test_tool_is_named_list() -> None:
    assert list_module.list_tool(_FakeFileSystem({})).name == "list"
