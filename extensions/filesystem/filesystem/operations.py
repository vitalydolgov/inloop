"""Filesystem operation wrappers."""

from pathlib import Path


def read(path: str) -> str:
    """Return the contents of a file."""
    return Path(path).expanduser().read_text()


def write(path: str, content: str) -> None:
    """Write content to a file, creating it if it does not exist."""
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def patch(path: str, old: str, new: str) -> None:
    """Replace the first occurrence of old with new in a file."""
    p = Path(path).expanduser()
    text = p.read_text()
    if old not in text:
        raise ValueError(f"text not found: {old!r}")
    p.write_text(text.replace(old, new, 1))
