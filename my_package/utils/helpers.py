"""General-purpose helper utilities.

Functions here are intentionally side-effect free and reusable across the
package. They follow the project's coding standards and use Google style
docstrings.
"""
from __future__ import annotations


def greet(name: str) -> str:
    """Return a friendly greeting message.

    Args:
        name: Person's name to greet.

    Returns:
        A greeting string addressing the provided name.
    """
    normalized = name.strip() or "there"
    return f"Hello, {normalized}!"
