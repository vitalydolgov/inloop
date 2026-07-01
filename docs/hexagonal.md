# Hexagonal ports

Ports are `Protocol` interfaces declared in `domain` or `app`. `infra` provides concrete implementations that satisfy them structurally, with no inheritance.

## `Model` — `inloop/domain/model.py`

A language model that answers a conversation as a stream of events.

## `Config` — `inloop/app/config.py`

Reads application configuration.

## `ExtensionRegistry` — `inloop/app/extensions.py`

Installs, removes, lists, and loads extensions.

## `Logger` — `inloop/app/logger.py`

Records entries produced while the agent runs.
