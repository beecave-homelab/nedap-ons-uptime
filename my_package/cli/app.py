"""Typer-based CLI application for `my_package`.

This module provides the main Typer application instance and a few example
commands to demonstrate structure and separation of concerns. It follows the
project's coding standards and uses Google style docstrings.
"""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from ..__about__ import __version__
from ..utils.helpers import greet

app = typer.Typer(help="my_package command-line interface")
console = Console()


def version_callback(value: bool) -> None:
    """Print the package version and exit if requested.

    Args:
        value: Whether the ``--version`` flag was provided.
    """
    if value:
        console.print(f"my_package {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(  # noqa: UP007 - Optional for clarity in help
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    """Root command callback.

    This executes before any subcommand and handles global options.

    Args:
        ctx: Typer context object.
        version: If provided, prints version and exits.
    """
    ctx.ensure_object(dict)


@app.command()
def hello(name: str = typer.Argument(..., help="Name to greet")) -> None:
    """Greet a user by name.

    Args:
        name: The name to greet.
    """
    message = greet(name)
    console.print(message)


if __name__ == "__main__":  # pragma: no cover
    app()
