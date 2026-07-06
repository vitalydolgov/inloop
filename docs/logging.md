# Logging

The agent depends on the `Logger` port in `app/logger.py`. Implement it to plug in a custom logger — as an adapter, it lives in `infra` and never has to touch `domain` or `app`.

It's optional. Omit it and the agent runs exactly as before, with no logging overhead.

## Agent ID

Each entry is tagged with the id of the agent that produced it: `main` for the top agent, `sub-1`, `sub-2`, … for the [subagents](loop.md) it spawns. Because a subagent shares its parent's logger, parent and children — including concurrent children — interleave in one log, told apart by that id.

## Built-in logger

`infra/plain_logger.py` is the bundled implementation. The main entrypoint wires it up by default, pointed at `var/log`.
