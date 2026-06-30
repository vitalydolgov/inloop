# Extensions

Each extension is an installable package that exposes an `EXTENSION` value and declares an `inloop.extensions` entry point. The loader discovers every installed package registered under that group — no manifest file required. Bundled extensions live in the [`inloop-builtin`](https://github.com/vitalydolgov/inloop-builtin) submodule at `extensions/`; external extensions live in their own repo. Both are registered the same way — an entry in the `extensions` group.

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

## Adding a testing CLI

Create `<module>/__main__.py` to test tools without starting the agent:

```python
from inloop import contrib

if __name__ == "__main__":
    contrib.program()()
```

```sh
uv run python -m <module> <tool_name> [key=value ...]
```

`key=value` pairs are parsed into a dict; integers are cast automatically (`page=2` → `{"page": 2}`).

## Tool descriptions

The `description=` field on `tool.Tool` is the only thing the model reads when deciding whether to call a tool — it is consumed by an AI, not a human, so every word should signal capability, trigger, or boundary. Write it as three sentences:

1. **What it does** — action verb + object + key mechanism, no filler. *"Fetches and returns the full text content of a single web page given a URL."*
2. **When to use it** — the concrete user intents, keywords, or scenarios that should fire this tool. Be specific; tools with overlapping purpose must read differently here. *"Use when the user provides a direct URL and wants to read, summarize, or extract information from that specific page."*
3. **Scope boundary** — what it does *not* cover, what the output looks like, and which sibling tool to prefer when another fits better. This sentence does the most work: the model already knows roughly what a tool can do from sentence 1, so the hard part is choosing between tools and knowing when to stop. *"Do not use for open-ended searches or when no URL is given; returns raw text, not rendered HTML — prefer `web_search` to discover URLs first."*

In one line: `[Does X via Y]. [Use when Z / user wants A, B, C]. [Does NOT cover D; output is E; prefer F when G].`

When adding a tool that resembles an existing one, make each description explicitly exclude the other's territory so the model can disambiguate. A trivial tool whose one-liner is self-evident (e.g. `add`) can keep a single sentence; anything with a real trigger or a sibling deserves all three.
