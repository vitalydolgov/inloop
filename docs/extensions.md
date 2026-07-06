# Extensions

Each extension is an installable package that exposes an `EXTENSION` value and declares an `inloop.extensions` entry point. The loader discovers every installed package registered under that group. Bundled extensions live in the [`inloop-builtin`](https://github.com/vitalydolgov/inloop-builtin) submodule at `extensions/` and are installed via the `bundled_extensions` uv dependency group. External extensions live in their own repo and are installed into local storage.

## Creating an extension

An extension is a standalone Python package with a module, an entry point, and an `EXTENSION` value:

```
greeter/
├── pyproject.toml
└── greeter/
    └── __init__.py
```

`pyproject.toml` declares the entry point and depends on `inloop-kit`, the extension toolkit — not the whole framework:

```toml
[project]
name = "greeter"
version = "0.1.0"
description = "Greets people by name."
requires-python = ">=3.11"
dependencies = ["inloop-kit"]

[project.entry-points."inloop.extensions"]
greeter = "greeter:EXTENSION"

[tool.uv.sources]
inloop-kit = { git = "https://github.com/vitalydolgov/inloop.git", subdirectory = "inloop_kit" }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

`inloop-kit` carries only the `Extension` and `tool` API an extension needs, with no runtime dependencies. It is not published to an index, so point at it with the git source above. Drop the `[tool.uv.sources]` block if you are developing the extension inside the `inloop-builtin` submodule, where bundled extensions reference the framework by path.

`greeter/__init__.py` wraps each function with `@tool` and collects them into an `EXTENSION`:

```python
"""Greeter extension: greet a person by name."""

from inloop_kit import Extension, tool


@tool(
    name="greet",
    description="Returns a friendly greeting addressed to the given name.",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The name of the person to greet.",
            },
        },
        "required": ["name"],
    },
)
def greet(args: dict[str, object]) -> str:
    return f"Hello, {args['name']}!"


EXTENSION = Extension(name="greeter", tools=[greet])
```

`@tool` turns a function into a tool. The function receives the parsed arguments as a dict and returns a string; a function annotated `-> None` returns `"ok"`. The agent calls each tool by its namespaced name, `<extension>__<tool>` (here `greeter__greet`). An exception raised by the function ends the turn as a `Failed` event rather than being fed back to the model.

### Tool descriptions

The `description=` field is the only thing the model reads when deciding whether to call a tool — it is consumed by an AI, not a human, so every word should signal capability, trigger, or boundary. Write it as three sentences:

1. **What it does** — action verb + object + key mechanism, no filler. *"Fetches and returns the full text content of a single web page given a URL."*
2. **When to use it** — the concrete user intents, keywords, or scenarios that should fire this tool. Be specific; tools with overlapping purpose must read differently here. *"Use when the user provides a direct URL and wants to read, summarize, or extract information from that specific page."*
3. **Scope boundary** — what it does *not* cover, what the output looks like, and which sibling tool to prefer when another fits better. This sentence does the most work: the model already knows roughly what a tool can do from sentence 1, so the hard part is choosing between tools and knowing when to stop. *"Do not use for open-ended searches or when no URL is given; returns raw text, not rendered HTML — prefer `web_search` to discover URLs first."*

In one line: `[Does X via Y]. [Use when Z / user wants A, B, C]. [Does NOT cover D; output is E; prefer F when G].`

When adding a tool that resembles an existing one, make each description explicitly exclude the other's territory so the model can disambiguate. A trivial tool whose one-liner is self-evident (e.g. `add`) can keep a single sentence; anything with a real trigger or a sibling deserves all three.

### Testing CLI

Run a tool from any installed extension without starting the agent:

```sh
uv run probe <extension> <tool_name> [key=value ...]
```

`key=value` pairs are parsed into a dict; integers and booleans are cast automatically (`page=2` → `{"page": 2}`, `force=true` → `{"force": True}`). Since path installs are editable, install an in-development extension once (`uv run extensions install ../greeter`) and source edits take effect on the next `probe` run.

## Installing an extension

An extension developed in its own repo can be installed from a path or git url, without touching this project's `pyproject.toml`:

```sh
uv run extensions install ../<extension>

# by git url (optionally pin a branch/tag/commit)
uv run extensions install "git+https://github.com/<you>/<extension>"
uv run extensions install "git+https://github.com/<you>/<extension>@v0.1.0"
```

This resolves the package and its dependencies into its own directory, recording its source in a registry file alongside it. A path source is installed editable — it keeps importing directly from that directory, so source edits take effect the next time this project runs, no reinstall needed. A git source is copied at the resolved revision.

Extensions are stored in the `extensions` subdirectory of the [inloop directory](../README.md#setup).

## Removing an extension

```sh
uv run extensions uninstall <name>
```

This deletes the extension's directory and its registry entry. Since discovery is entry-point-based, the extension stops being loaded immediately — nothing else to clean up.

## Listing installed extensions

```sh
uv run extensions list
```

Lists both externally-installed extensions (with their source) and bundled extensions (marked `bundled`).
