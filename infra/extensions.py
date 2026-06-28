"""Loads the extensions declared in an extensions.toml manifest."""

import importlib
import tomllib
from pathlib import Path

from domain import extension

ATTRIBUTE = "EXTENSION"


def load(manifest: Path) -> list[extension.Extension]:
    """Import every module declared in the manifest and collect its extension."""
    declared = tomllib.loads(manifest.read_text())
    modules = declared.get("extensions", [])
    return [getattr(importlib.import_module(name), ATTRIBUTE) for name in modules]
