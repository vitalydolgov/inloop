"""Tests for the arithmetic expression evaluator."""

import asyncio

from calculator import evaluate


def _execute(expression):
    return asyncio.run(evaluate.execute({"expression": expression}))


def test_addition():
    assert _execute("2 + 3") == "5"


def test_subtraction():
    assert _execute("10 - 4") == "6"


def test_multiplication():
    assert _execute("3 * 4") == "12"


def test_division():
    assert _execute("10 / 4") == "2.5"


def test_floor_division():
    assert _execute("10 // 3") == "3"


def test_modulo():
    assert _execute("10 % 3") == "1"


def test_exponentiation():
    assert _execute("2 ** 8") == "256"


def test_operator_precedence():
    assert _execute("2 + 2 * 3") == "8"


def test_unary_negation():
    assert _execute("-5") == "-5"


def test_unary_plus():
    assert _execute("+5") == "5"


def test_nested_expression():
    assert _execute("(2 + 3) * 4") == "20"


def test_division_by_zero():
    assert _execute("1 / 0") == "division by zero"


def test_invalid_syntax():
    assert "invalid syntax" in _execute("2 +")


def test_unsupported_expression():
    assert _execute("x + 1") == "unsupported expression"
