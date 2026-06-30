"""A calculator tool the model can request to evaluate arithmetic."""

from inloop import contrib

from calculator import evaluate

evaluate = contrib.Tool(
    name="evaluate",
    description="Evaluate a basic arithmetic expression and return the result.",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The arithmetic expression to evaluate, e.g. '2 + 2 * 3'.",
            },
        },
        "required": ["expression"],
    },
    execute=evaluate.evaluate,
)

EXTENSION = contrib.Extension(name="calculator", tools=[evaluate])
