"""Main entry point for the CLI application."""
import typer
from cli.commands import example
from cli.commands import auth
from cli.commands import system
from cli.config import get_token_last_updated, auto_authenticate
from datetime import datetime, timedelta


app = typer.Typer(help="CLI for interacting with the generated API client.")

app.add_typer(auth.auth_app, name="auth")
app.add_typer(example.example_app, name="example")
app.add_typer(system.system_app, name="system")


def main():
    """Run the CLI application."""
    # Global token refresh logic
    last_updated = get_token_last_updated()
    if not last_updated or (datetime.utcnow() - last_updated > timedelta(hours=24)):
        print("[cyan]Refreshing authorization token...[/cyan]")
        auto_authenticate()
    app()


if __name__ == "__main__":
    main()

# TODO: Register additional commands as modules are added 