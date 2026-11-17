#!/usr/bin/env python3
"""Example Python file demonstrating basic concepts."""


def greet(name: str) -> str:
    """Return a greeting message."""
    return f"Ciao, {name}!"


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


class Calculator:
    """Simple calculator class."""

    def __init__(self):
        self.history = []

    def compute(self, a: int, b: int, op: str) -> float:
        """Perform a calculation and store in history."""
        ops = {
            "+": lambda x, y: x + y,
            "-": lambda x, y: x - y,
            "*": lambda x, y: x * y,
            "/": lambda x, y: x / y if y != 0 else float("inf"),
        }
        result = ops.get(op, lambda x, y: None)(a, b)
        self.history.append(f"{a} {op} {b} = {result}")
        return result


if __name__ == "__main__":
    # Function examples
    print(greet("Mondo"))
    print(f"2 + 3 = {add(2, 3)}")

    # Class example
    calc = Calculator()
    print(calc.compute(10, 5, "+"))
    print(calc.compute(10, 5, "*"))
    print("History:", calc.history)