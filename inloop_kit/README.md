# inloop-kit

The toolkit for building [inloop](https://github.com/vitalydolgov/inloop) extensions.

An extension declares its tools with `@tool` and collects them into an `Extension`,
depending only on this package — not the rest of the framework:

```python
from inloop_kit import Extension, tool


@tool(
    name="greet",
    description="Returns a friendly greeting addressed to the given name.",
    parameters={
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    },
)
def greet(args: dict[str, object]) -> str:
    return f"Hello, {args['name']}!"


EXTENSION = Extension(name="greeter", tools=[greet])
```

See [docs/extensions.md](https://github.com/vitalydolgov/inloop/blob/main/docs/extensions.md).
