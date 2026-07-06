# Logging

The application keeps two separate logs. The **run log** records what happens while the agent runs — the user input, the model output, and the tool calls — through a port the agent writes to. The **MCP server log** captures the error output of any tool server the agent launches, written directly rather than through that port. This document describes both. Both land in the [inloop directory](../README.md#setup)'s `log` subdirectory.

## Run log

The agent logs through the `Logger` port in `app/logger.py`. Logging is optional: leave the port unset and the agent runs unchanged.

The agent writes through the `Logger` port in `app/logger.py`. Each entry is tagged with the id of the agent that produced it, so a spawned subagent's activity stays distinguishable from its parent's. Because a subagent shares its parent's logger, parent and children — including concurrent ones — interleave in a single log, told apart by that id: `main` for the top agent, `sub-1`, `sub-2`, … for the subagents it spawns.

### `PlainLogger`

`infra/plain_logger.py` is the bundled adapter, wired up by default. It writes one file per run and appends a timestamped line per entry, folding streamed deltas into their phase so each thinking or text phase is recorded once, in full.

## MCP server log

A stdio MCP server runs as a child process. `McpToolServer` (`infra/mcp_server.py`) captures its error output to `mcp-server.log`, shared across servers. This bypasses the `Logger` port — it is the server's own output, not the agent's.
