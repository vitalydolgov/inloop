# Extensions

Each extension is an installable package that exposes an `EXTENSION` value and declares an `inloop.extensions` entry point. The loader discovers every installed package registered under that group — no manifest file required. Bundled extensions live under `extensions/` as uv workspace members; external extensions live in their own repo and are installed by path or git url.

## Installing an external extension

An extension developed in its own repo only needs to be installed into this project's environment. Use native uv to install from a path or git url:

```sh
# by path (use --editable while co-developing both repos)
uv add --group extensions --editable ../<extension>

# by git url (optionally pin a branch/tag/commit)
uv add --group extensions "git+https://github.com/<you>/<extension>"
uv add --group extensions "git+https://github.com/<you>/<extension>@v0.1.0"
```

This records the package under the `extensions` dependency group plus a matching `[tool.uv.sources]` entry in the root `pyproject.toml`. The extension is picked up automatically on next run.

## Removing an external extension

```sh
uv remove --group extensions <extension>
```

This removes the package from `pyproject.toml` and uninstalls it. Since discovery is entry-point-based, the extension stops being loaded immediately — nothing else to clean up.

## Adding a bundled extension

**1. Create `extensions/<extension>/pyproject.toml`**

```toml
[project]
name = "<extension>"
...
dependencies = ["inloop"]

[project.entry-points."inloop.extensions"]
<extension> = "<module>:EXTENSION"

[build-system]  # required — uv won't install the extension without it; any PEP 517 backend works
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv.sources]
inloop = { workspace = true }  # resolve from the local workspace, not PyPI
```

**2. Create `extensions/<extension>/<module>/__init__.py`**

`__init__.py` is the entry point and must export `EXTENSION`.

```python
from domain import extension, tool

_my_tool = tool.Tool(
    name="<extension>",
    description="What this tool does.",
    parameters={"type": "object", "properties": {...}, "required": [...]},
    execute=lambda args: "result",
)

EXTENSION = extension.Extension(name="<extension>", tools=[_my_tool])
```

**3. Register in the root `pyproject.toml`**

```toml
[tool.uv.sources]
<extension> = { workspace = true }  # resolve from the local workspace, not PyPI

[dependency-groups]
extensions = ["<extension>"]  # uv won't install a workspace member unless it appears as a dependency
```

**4. Sync**

```sh
uv sync
```

## Removing a bundled extension

1. Delete `extensions/<extension>/`
2. Remove `<extension>` from `[dependency-groups] extensions` and `[tool.uv.sources]` in the root `pyproject.toml`
3. Run `uv sync`

## Tool descriptions

The `description=` field on `tool.Tool` is the only thing the model reads when deciding whether to call a tool — it is consumed by an AI, not a human, so every word should signal capability, trigger, or boundary. Write it as three sentences:

1. **What it does** — action verb + object + key mechanism, no filler. *"Fetches and returns the full text content of a single web page given a URL."*
2. **When to use it** — the concrete user intents, keywords, or scenarios that should fire this tool. Be specific; tools with overlapping purpose must read differently here. *"Use when the user provides a direct URL and wants to read, summarize, or extract information from that specific page."*
3. **Scope boundary** — what it does *not* cover, what the output looks like, and which sibling tool to prefer when another fits better. This sentence does the most work: the model already knows roughly what a tool can do from sentence 1, so the hard part is choosing between tools and knowing when to stop. *"Do not use for open-ended searches or when no URL is given; returns raw text, not rendered HTML — prefer `web_search` to discover URLs first."*

In one line: `[Does X via Y]. [Use when Z / user wants A, B, C]. [Does NOT cover D; output is E; prefer F when G].`

When adding a tool that resembles an existing one, make each description explicitly exclude the other's territory so the model can disambiguate. A trivial tool whose one-liner is self-evident (e.g. `add`) can keep a single sentence; anything with a real trigger or a sibling deserves all three.
