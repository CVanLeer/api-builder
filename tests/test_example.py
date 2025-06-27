from typer.testing import CliRunner
from cli.main import app

runner = CliRunner()

def test_hello():
    result = runner.invoke(app, ["example", "hello", "World"])
    assert result.exit_code == 0
    assert "Hello, World!" in result.output 