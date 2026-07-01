"""Installs, removes, discovers, and loads extensions in isolated directories."""

import json
import shutil
import site
import subprocess
import tempfile
from importlib.metadata import PathDistribution, entry_points
from pathlib import Path

from inloop.domain import extension

GROUP = "inloop.extensions"


class DirectoryExtensionRegistry:
    """Manages extensions, each installed in its own isolated directory."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._registry_path = root / "registry.json"

    def install(self, source: str) -> str:
        """Install an extension from a path or git url and return its package name; path sources stay linked live."""
        editable = Path(source).expanduser().exists()

        self._root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=self._root) as staging:
            self._pip_install(Path(staging), source, deps=False, editable=editable)
            name = self._installed_name(Path(staging))

        target = self._root / name
        shutil.rmtree(target, ignore_errors=True)
        self._pip_install(target, source, deps=True, editable=editable)

        registry = self._read_registry()
        registry[name] = source
        self._write_registry(registry)
        return name

    def uninstall(self, name: str) -> None:
        """Remove an installed extension."""
        shutil.rmtree(self._root / name, ignore_errors=True)
        registry = self._read_registry()
        registry.pop(name, None)
        self._write_registry(registry)

    def installed(self) -> dict[str, str]:
        """Return installed extension names mapped to the source they were installed from."""
        return self._read_registry()

    def paths(self) -> list[Path]:
        """Return the directory of every installed extension."""
        return [self._root / name for name in self._read_registry()]

    def load(self) -> list[extension.Extension]:
        """Load every installed extension registered in the inloop.extensions group."""
        for path in self.paths():
            site.addsitedir(str(path))
        return [ep.load() for ep in entry_points(group=GROUP)]

    def _read_registry(self) -> dict[str, str]:
        if not self._registry_path.exists():
            return {}
        return json.loads(self._registry_path.read_text())

    def _write_registry(self, registry: dict[str, str]) -> None:
        self._registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True))

    def _pip_install(self, target: Path, source: str, *, deps: bool, editable: bool) -> None:
        args = ["uv", "pip", "install", "--target", str(target)]
        if not deps:
            args.append("--no-deps")
        if editable:
            args.append("--editable")
        args.append(source)
        subprocess.run(args, check=True)

    def _installed_name(self, target: Path) -> str:
        [dist_info] = list(target.glob("*.dist-info"))
        return PathDistribution(dist_info).metadata["Name"]
