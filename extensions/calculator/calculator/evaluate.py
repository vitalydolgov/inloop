"""Arithmetic expression evaluator."""

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
    """Evaluate a node of a parsed arithmetic expression."""
    match node:
        case ast.Constant(value) if isinstance(value, (int, float)):
            return value
        case ast.BinOp(left, op, right) if type(op) in _BINARY:
            return _BINARY[type(op)](_evaluate(left), _evaluate(right))
        case ast.UnaryOp(op, operand) if type(op) in _UNARY:
            return _UNARY[type(op)](_evaluate(operand))
        case _:
            raise ValueError("unsupported expression")


@contrib.rescue
def evaluate(args: dict[str, object]) -> str:
    """Evaluate the requested arithmetic expression and return its result."""
    expression = str(args["expression"])
    return str(_evaluate(ast.parse(expression, mode="eval").body))
