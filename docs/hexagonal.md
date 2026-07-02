# Ports and Adapters

Ports are `Protocol` interfaces declared in `domain` or `app`. `infra` provides concrete implementations that satisfy them structurally, with no inheritance.

## `Model` — `domain/model.py`

A language model that answers a conversation as an async stream of events.

## `Config` — `app/config.py`

Reads application configuration.

## `ExtensionRegistry` — `app/extensions.py`

Installs, removes, lists, and loads extensions.

## `Logger` — `app/logger.py`

Records entries produced while the agent runs.
