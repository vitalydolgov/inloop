"""Install, remove, and list extensions stored outside the uv project."""

import argparse

from inloop.infra import toml_config
from inloop.infra.directory_registry import DirectoryExtensionRegistry


def main() -> None:
    """Run the extension management command."""
    parser = argparse.ArgumentParser(prog="extensions")
    subcommands = parser.add_subparsers(dest="command", required=True)

    install = subcommands.add_parser("install", help="Install an extension from a path or git url")
    install.add_argument("source")

    uninstall = subcommands.add_parser("uninstall", help="Remove an installed extension")
    uninstall.add_argument("name")

    subcommands.add_parser("list", help="List installed extensions")

    args = parser.parse_args()
    config = toml_config.TomlConfig(toml_config.default_path())
    storage = DirectoryExtensionRegistry(config.extensions.path())

    match args.command:
        case "install":
            name = storage.install(args.source)
            print(f"Installed {name}")
        case "uninstall":
            storage.uninstall(args.name)
            print(f"Uninstalled {args.name}")
        case "list":
            installed = storage.installed()
            bundled = {ext.name: "bundled" for ext in storage.load() if ext.name not in installed}
            for name, source in sorted((installed | bundled).items()):
                print(f"{name} ({source})")
