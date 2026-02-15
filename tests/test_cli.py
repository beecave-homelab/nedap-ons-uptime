"""CLI tests for `my_package` using Typer's CliRunner."""
from typer.testing import CliRunner

from my_package.cli import app

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])  # type: ignore[arg-type]
    assert result.exit_code == 0
    assert "my_package command-line interface" in result.stdout


def test_cli_version() -> None:
    result = runner.invoke(app, ["--version"])  # type: ignore[arg-type]
    assert result.exit_code == 0
    assert "my_package" in result.stdout


def test_cli_hello() -> None:
    result = runner.invoke(app, ["hello", "Alice"])  # type: ignore[arg-type]
    assert result.exit_code == 0
    assert "Hello, Alice!" in result.stdout
