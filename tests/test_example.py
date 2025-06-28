"""Test suite for example CLI commands."""
from typer.testing import CliRunner
from cli.main import app

runner = CliRunner()


def test_hello():
    """Test the hello command output."""
    result = runner.invoke(app, ["example", "hello", "World"])
    assert result.exit_code == 0
    assert "Hello, World!" in result.output 