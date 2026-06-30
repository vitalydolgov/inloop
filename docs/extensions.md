# Extensions

Each extension is an installable package that exposes an `EXTENSION` value and declares an `inloop.extensions` entry point. The loader discovers every installed package registered under that group — no manifest file required. Bundled extensions live in the [`inloop-builtin`](https://github.com/vitalydolgov/inloop-builtin) submodule at `extensions/`; external extensions live in their own repo. Both are registered the same way — an entry in the `extensions` group.

## Creating an extension

An extension is a standalone Python package with a module, an entry point, and an `EXTENSION` value:

```
greeter/
├── pyproject.toml
└── greeter/
    └── __init__.py
```

`pyproject.toml` declares the entry point and depends on `inloop`:

```toml
[project]
name = "greeter"
version = "0.1.0"
description = "Greets people by name."
requires-python = ">=3.13"
dependencies = ["inloop"]

[project.entry-points."inloop.extensions"]
greeter = "greeter:EXTENSION"

[tool.uv.sources]
inloop = { git = "https://github.com/vitalydolgov/inloop.git" }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

`inloop` is not published to an index, so point at it with the git source above. Drop the `[tool.uv.sources]` block if you are developing the extension inside the `inloop-builtin` submodule, where bundled extensions reference the framework by path.

`greeter/__init__.py` wraps each function with `@contrib.tool` and collects them into an `EXTENSION`:

```python
"""Greeter extension: greet a person by name."""

from inloop import contrib


@contrib.tool(
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


EXTENSION = contrib.Extension(name="greeter", tools=[greet])
```

`@contrib.tool` turns a function into a tool. The function receives the parsed arguments as a dict and returns a string; a function annotated `-> None` returns `"ok"`, and any exception is caught and returned as an error string. The agent calls each tool by its namespaced name, `<extension>__<tool>` (here `greeter__greet`).

### Tool descriptions

The `description=` field is the only thing the model reads when deciding whether to call a tool — it is consumed by an AI, not a human, so every word should signal capability, trigger, or boundary. Write it as three sentences:

1. **What it does** — action verb + object + key mechanism, no filler. *"Fetches and returns the full text content of a single web page given a URL."*
2. **When to use it** — the concrete user intents, keywords, or scenarios that should fire this tool. Be specific; tools with overlapping purpose must read differently here. *"Use when the user provides a direct URL and wants to read, summarize, or extract information from that specific page."*
3. **Scope boundary** — what it does *not* cover, what the output looks like, and which sibling tool to prefer when another fits better. This sentence does the most work: the model already knows roughly what a tool can do from sentence 1, so the hard part is choosing between tools and knowing when to stop. *"Do not use for open-ended searches or when no URL is given; returns raw text, not rendered HTML — prefer `web_search` to discover URLs first."*

In one line: `[Does X via Y]. [Use when Z / user wants A, B, C]. [Does NOT cover D; output is E; prefer F when G].`

When adding a tool that resembles an existing one, make each description explicitly exclude the other's territory so the model can disambiguate. A trivial tool whose one-liner is self-evident (e.g. `add`) can keep a single sentence; anything with a real trigger or a sibling deserves all three.

### Testing CLI

Create `<module>/__main__.py` to test tools without starting the agent:

```python
from inloop import contrib

if __name__ == "__main__":
    contrib.program()()
```

```sh
uv run python -m <module> <tool_name> [key=value ...]
```

`key=value` pairs are parsed into a dict; integers and booleans are cast automatically (`page=2` → `{"page": 2}`, `force=true` → `{"force": True}`).

## Installing an extension

An extension developed in its own repo only needs to be installed into this project's environment. Use native uv to install from a path or git url:

```sh
# by path (use --editable while co-developing both repos)
uv add --group extensions --editable ../<extension>

# by git url (optionally pin a branch/tag/commit)
uv add --group extensions "git+https://github.com/<you>/<extension>"
uv add --group extensions "git+https://github.com/<you>/<extension>@v0.1.0"
```

This records the package under the `extensions` dependency group plus a matching `[tool.uv.sources]` entry in the root `pyproject.toml`. The extension is picked up automatically on next run.

## Removing an extension

```sh
uv remove --group extensions <extension>
```

This removes the package from `pyproject.toml` and uninstalls it. Since discovery is entry-point-based, the extension stops being loaded immediately — nothing else to clean up.
