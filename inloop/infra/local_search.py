"""Searches file contents on the local disk by regular expression."""

import re
from fnmatch import fnmatch
from pathlib import Path

from inloop.app.search import Match


class LocalSearch:
    """A Search that walks the local disk and matches file contents by regular expression."""

    def search(self, pattern: str, path: str, glob: str | None = None) -> list[Match]:
        """Return the lines under path matching the pattern, limited to files whose name matches glob when given."""
        root = Path(path)
        if not root.exists():
            raise FileNotFoundError(path)
        regex = re.compile(pattern)
        files = sorted(root.rglob("*")) if root.is_dir() else [root]
        matches = []
        for file in files:
            if not file.is_file():
                continue
            if glob and not fnmatch(file.name, glob):
                continue
            try:
                text = file.read_text()
            except (OSError, UnicodeDecodeError):
                continue
            for number, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    matches.append(Match(str(file), number, line))
        return matches
