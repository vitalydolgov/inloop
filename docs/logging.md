# Logging

The agent depends on the `Logger` port in `app/log.py`. Implement it to plug in a custom logger — as an adapter, it lives in `infra` and never has to touch `domain` or `app`.

It's optional. Omit it and the agent runs exactly as before, with no logging overhead.

## Built-in logger

`infra/plain_logger.py` is the bundled implementation. The demo entrypoint wires it up by default, pointed at `var/log`.
