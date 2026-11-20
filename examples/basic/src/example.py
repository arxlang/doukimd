"""
title: Example API
summary: A small project documented with Douki.
"""

from public import private, public


@public
def add(left: int, right: int = 0) -> int:
    """
    title: Add two integers.
    summary: Return the sum of the arguments.
    parameters:
      left:
        description: First value.
      right:
        description: Second value.
        default: 0
    returns:
      description: The sum.
    examples:
    - code: add(2, 3)
    """
    return left + right


@private
def helper() -> None:
    """
    title: An explicitly private helper.
    """
