"""Tests for the built-in filesystem find tool."""

import asyncio

from inloop.app.builtin.filesystem import find


class _FakeFileSystem:
    """A FileSystem serving file paths from an in-memory mapping."""

    def __init__(self, matches: dict[tuple[str, str], list[str]]) -> None:
        self._matches = matches

    def find(self, path: str, pattern: str) -> list[str]:
        key = (path, pattern)
        if key not in self._matches:
            raise FileNotFoundError(path)
        return self._matches[key]


def _find(matches: dict[tuple[str, str], list[str]], args: dict[str, object]) -> str:
    tool = find.find_tool(_FakeFileSystem(matches))
    return asyncio.run(tool.execute(args))


def test_returns_matching_files_in_sorted_order() -> None:
    out = _find(
        {(".", "*.py"): ["tests/test.py", "inloop/main.py"]},
        {"pattern": "*.py"},
    )

    assert out == "inloop/main.py\ntests/test.py"


def test_searches_below_the_requested_path() -> None:
    out = _find(
        {("src", "README.md"): ["src/docs/README.md"]},
        {"path": "src", "pattern": "README.md"},
    )

    assert out == "src/docs/README.md"


def test_reports_when_there_are_no_matches() -> None:
    out = _find({(".", "*.py"): []}, {"pattern": "*.py"})

    assert out == "No files found"


def test_empty_pattern_returns_an_error_message() -> None:
    out = _find({}, {"pattern": ""})

    assert out == "Error: `pattern` must not be empty"


def test_find_failure_returns_an_error_message() -> None:
    out = _find({}, {"path": "missing", "pattern": "*.py"})

    assert out.startswith("Error: could not find files under missing")


def test_tool_is_named_find() -> None:
    assert find.find_tool(_FakeFileSystem({})).name == "find"
