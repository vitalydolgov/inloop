This is a Python project managed with uv.

## Architecture

Project follows Domain-Driven Design (DDD) with this layout:
- `domain`  - core concepts and their behavior
- `app`     - workflows that coordinate domain behavior
- `infra`   - concrete implementations of domain and app ports
- `demo`    - showcase of system capabilities

Dependency rules:
- `domain` must not import from any other layer — it has zero dependencies on the rest of the project.
- `app` must not import from `infra` or `demo` — it only coordinates domain concepts.

## Python conventions

- Docstrings should describe what something does or what it is — not how it works or what its parameters are.
- Do not document helper functions.
- Import modules directly — do not use `__init__.py` to re-export or aggregate imports.
- When returning a sequence, always use a list — never a tuple.

## Testing

- Write tests only for `domain` and `app`, do not test `infra` unless explicitly requested.

## Documentation

- Write documentation that stands alone — don't cite or assume CLAUDE.md.
- Omit what the reader already knows — from the code (signatures, formats, behavior) or from domain familiarity. Point to the implementation instead of restating it.