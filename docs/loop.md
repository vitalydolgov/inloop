# The agent loop

`Agent.events(messages)` in `app/agent.py` drives the loop. It takes an async stream of user messages and returns an async stream of `streaming.Event`s — the caller feeds input and renders output, nothing more.

## Interaction and turns

An **interaction** (`app/interaction.py`) is the exchange between the user and the agent for a stream of messages. It owns the inbox (`app/inbox.py`), folds mid-run input in as [steering](#steering), and runs **turns** until the agent is idle after each user message.

A **turn** (`app/turn.py`) is one pass over the model. It asks a **turn source** (`app/turn_source.py`) for the tools available right now and for a model stream over the conversation it is folding into, with those tools and the system prompt. The agent builds that source once and hands it to the interaction.

1. The model streams against the current conversation.
2. If it requests tools — including [spawning a subagent](#subagents) — they run concurrently and their results are appended to the conversation.
3. If tools ran, the interaction starts another turn with those results in context.

Turns continue until the model stops without calling a tool. A user message starts work only when the agent is idle; one that arrives while a response is running is folded in as steering.

## Events

The stream reports what the model is doing as it happens, defined in `domain/streaming.py`: phase markers and deltas for thinking and visible text, `ToolUse` for each tool request, and one terminal event per turn — `MessageCompleted`, `Interrupted`, or `Failed`.

## Commands

A message that starts with `/` is addressed to the harness, not the model: the interaction runs the matching `Command` (`app/command.py`) and reports back with a `CommandCompleted` event (the command name only), leaving the conversation untouched. An unknown command, or one that fails, comes back as `Failed`.

Commands are handed to the agent by whoever composes it, which is what keeps the agent itself unaware of what any of them do. A command's `run` is a side effect — it does not return user-facing text. Today the only one is `/reload`, which rebuilds the tools from the configured [MCP servers](mcp.md). Each turn asks the turn source again, so the new set is what the next message sees. Steering text is never taken for a command — only a message that opens a response.

## Steering

A message that arrives while a response is streaming is not held until the response finishes. It is injected as a user message between turns, so you can redirect the agent mid-task without waiting for it to come up for air. A message sent during a plain text turn — one with no tool calls — opens the next response instead, since there is no tool boundary to inject at.

## Interrupt

`interrupt()` — `Ctrl+C` in the CLI — asks the current response to stop as soon as possible. In-flight tool calls are cancelled at the next await; an `Interrupted` event is emitted without committing partial tool results. The signal cascades to any running subagents.

## Compaction

Long sessions eventually approach the model's context window. When a completed pass exceeds a fraction of `context_window` (see `app/compaction.py`), the agent summarizes older turns into a compact briefing that replaces them, keeping the current turn and any in-flight tool exchange verbatim. The check runs after every completed pass, so a long tool-using turn can be compacted mid-flight. A `Compaction.STARTED`/`Compaction.ENDED` pair brackets the work.

Compaction is enabled when the model reports a positive context window; a window of `0` disables it.

## Subagents

The agent can delegate a scoped task to a subagent through the built-in `agent__spawn` tool. The subagent is a fresh agent that runs its own loop over a single message — the task — with the same extensions and tools but its own conversation. It works the task to completion and returns its final reply as the tool result, so from the parent's side delegation is just one tool call.

It uses the parent's subagent model if one was configured, otherwise the same model, and it cannot spawn further subagents — delegation is one level deep. If it fails, the parent gets an error string in place of an answer; if it is interrupted, it returns whatever it had produced so far.
