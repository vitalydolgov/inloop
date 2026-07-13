This is a Python project managed with uv.

- Run Python scripts and checks through uv (`uv run python ...`).
- Before writing or editing documentation, read `docs/instructions.md`.

## Architecture

Project follows Domain-Driven Design (DDD) with a hexagonal (ports-and-adapters) structure:
- `domain`  - core concepts and their behavior
- `app`     - workflows that coordinate domain behavior
- `infra`   - concrete implementations of domain and app ports
- `demo`    - showcase of system capabilities
- `cmd`     - entry points for configuration utilities

Dependency rules:
- `domain` must not import from any other layer — it has zero dependencies on the rest of the project.
- `app` must not import from `infra` — it only coordinates domain concepts.
- Dependencies point inward: `infra` and `demo` depend on `app` and `domain`, never the reverse.

### Ports and adapters

- Every capability `infra` provides must be exposed through a `Protocol` port owned by its consumer (`domain` for business behavior, `app` for operational concerns), with `infra` supplying only the implementation (the adapter). Never a bare function or class in `infra` with no port behind it.
- Ports are the boundary of the hexagon: the core (`domain` + `app`) defines the interfaces it needs, and adapters in `infra` implement them. This is what lets the core stay ignorant of concrete technology (databases, HTTP, message brokers, etc.).
- Keep `docs/hexagonal.md` in sync whenever a port or its implementation changes.

## Python conventions

- Docstrings should describe what something does or what it is — not how it works or what its parameters are.
- Do not document helper functions.
- Import modules directly — do not use `__init__.py` to re-export or aggregate imports.
- When a public interface accepts or returns a sequence, use a list — never a tuple or `Sequence`.
- Prefer a `for` loop over a comprehension; use a comprehension only when it is more efficient or can be passed as an expression.

### Type annotations

- Don't annotate private methods and functions (prefixed `_`) with types — only public ones.
- Don't annotate a `-> None` return type.
- Don't annotate a local variable with a port's `Protocol` type when assigning it a concrete implementation.

## Testing

- Write tests only for `domain` and `app`, do not test `infra` unless explicitly requested.
- When running the interactive executable (`uv run inloop`), pass `--no-banner`.

## Communication style

- Avoid jargon. Only use a specialized term if it is widely recognized among software developers — meaning it appears regularly in conference talks, published books, and mainstream technical writing without needing explanation.
- When in doubt, use the simpler word. Do not use acronyms, internal project codenames, or vendor-specific buzzwords unless they are already common in published literature and conference keynotes.

## Repository

- Commit messages are a single title line only — no body.
- Keep only the essential action and object in the title; drop trailing qualifiers that add detail without disambiguating the change.

## Shell

- BSD `sed` doesn't support `\b` word boundaries. For whole-identifier renames across files, use `perl -pi -e 's/\bOld\b/New/g'` instead.
- BSD `cat` doesn't support the `-A` flag. To inspect non-printing characters, use `vis` instead.