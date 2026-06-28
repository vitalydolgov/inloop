"""Tests for the arithmetic expression evaluator."""

import pytest

from calculator import evaluate


def test_addition():
    assert evaluate.execute({"expression": "2 + 3"}) == "5"


def test_subtraction():
    assert evaluate.execute({"expression": "10 - 4"}) == "6"


def test_multiplication():
    assert evaluate.execute({"expression": "3 * 4"}) == "12"


def test_division():
    assert evaluate.execute({"expression": "10 / 4"}) == "2.5"


def test_floor_division():
    assert evaluate.execute({"expression": "10 // 3"}) == "3"


def test_modulo():
    assert evaluate.execute({"expression": "10 % 3"}) == "1"


def test_exponentiation():
    assert evaluate.execute({"expression": "2 ** 8"}) == "256"


def test_operator_precedence():
    assert evaluate.execute({"expression": "2 + 2 * 3"}) == "8"


def test_unary_negation():
    assert evaluate.execute({"expression": "-5"}) == "-5"


def test_unary_plus():
    assert evaluate.execute({"expression": "+5"}) == "5"


def test_nested_expression():
    assert evaluate.execute({"expression": "(2 + 3) * 4"}) == "20"


def test_division_by_zero():
    assert evaluate.execute({"expression": "1 / 0"}).startswith("error:")


def test_invalid_syntax():
    assert evaluate.execute({"expression": "2 +"}).startswith("error:")


def test_unsupported_expression():
    assert evaluate.execute({"expression": "x + 1"}).startswith("error:")
