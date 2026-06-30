"""Calculator extension: evaluate arithmetic expressions."""

import ast
import operator

from inloop import contrib

_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _evaluate(node: ast.expr) -> float:
    match node:
        case ast.Constant(value) if isinstance(value, (int, float)):
            return value
        case ast.BinOp(left, op, right) if type(op) in _BINARY:
            return _BINARY[type(op)](_evaluate(left), _evaluate(right))
        case ast.UnaryOp(op, operand) if type(op) in _UNARY:
            return _UNARY[type(op)](_evaluate(operand))
        case _:
            raise ValueError("unsupported expression")


@contrib.tool(
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
)
def evaluate(args: dict[str, object]) -> str:
    expression = str(args["expression"])
    return str(_evaluate(ast.parse(expression, mode="eval").body))


EXTENSION = contrib.Extension(name="calculator", tools=[evaluate])
