# Testing

There are two kinds of tests here, with different expectations for when each is written.

**Core-layer tests are unconditional.** Every behavior change to the core layers gets a test. They fake the ports those layers depend on instead of touching anything real, so they run in milliseconds as part of the default test run.

**Adapter tests are opt-in.** An adapter is only tested when someone explicitly asks for coverage there, since most of what an adapter does is translate to and from a third-party shape — testing that honestly means either building a fake worth as much effort as the adapter itself, or exercising the real thing. Both approaches show up, chosen per adapter:

- When an adapter's dependency is itself cheap to fake (a local resource like the filesystem), it's tested in-process against that fake. No network, no special marker, runs every time.
- When an adapter wraps a third-party service, no in-process fake can stand in for the real wire contract closely enough to be worth trusting, so it's tested against the live backend instead. These need real credentials, cost real usage, and are excluded from the default run by a dedicated marker — run them deliberately, not as a matter of course.

Standalone packages that plug into the framework sit outside both categories — each tests its own behavior independently, on its own terms.

## Running tests

```sh
uv run pytest
```

This runs everything except the tests that hit a real external service, which are excluded by default. Scope the run to the part of the tree you're iterating on — a bare run from the repo root also picks up any installed packages that ship their own tests, which usually isn't what you want.

Common variants:

```sh
uv run pytest <path>      # one module or directory
uv run pytest -k <name>   # by test name
uv run pytest -v          # list each test as it runs
```

### Real-backend tests

```sh
uv sync --extra anthropic
export ANTHROPIC_API_KEY="..."
uv run pytest -m anthropic
```

```sh
uv run pytest -m deepwiki
```

These call a live backend (or a public remote service) and may incur costs, which is why they're opt-in rather than part of the default run. The `anthropic` marker needs a real API key; `deepwiki` hits the public DeepWiki MCP server and needs network access.
