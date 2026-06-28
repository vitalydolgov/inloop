"""A calculator tool the model can request to evaluate arithmetic."""

from domain import extension
from domain import tool

from calculator import evaluate

evaluate = tool.Tool(
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
    execute=evaluate.execute,
)

EXTENSION = extension.Extension(name="calculator", tools=[evaluate])
