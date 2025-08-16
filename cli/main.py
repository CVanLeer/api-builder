"""Main entry point for the CLI application."""
import typer
from cli.commands import example
from cli.commands import auth
from cli.commands import system
from cli.config import get_token_last_updated, auto_authenticate
from datetime import datetime, timedelta


app = typer.Typer(
    help="🚀 API Builder - Intelligent API integration platform that transforms any API documentation into a working Python SDK with CLI interface.",
    epilog="💡 Get started: 'python cli/main.py auth get-token' then 'python cli/main.py system query-api'",
    rich_markup_mode="rich"
)

app.add_typer(auth.auth_app, name="auth")
app.add_typer(example.example_app, name="example")
app.add_typer(system.system_app, name="system")


def main():
    """
    Run the CLI application with automatic token refresh.

    This function serves as the main entry point for the API Builder CLI.
    It automatically refreshes expired authentication tokens and then
    launches the Typer application with all registered command groups.

    The token refresh logic checks if the stored token is older than 24 hours
    and automatically re-authenticates if needed, ensuring seamless API access.

    Example:
        Run the CLI directly:
        >>> main()
        
        Or from command line:
        $ python cli/main.py --help
        $ python cli/main.py auth get-token
        $ python cli/main.py system query-api

    Note:
        This function will exit with an error code if authentication fails
        or if required dependencies are missing.
    """
    # Global token refresh logic
    last_updated = get_token_last_updated()
    if not last_updated or (datetime.utcnow() - last_updated > timedelta(hours=24)):
        print("[cyan]Refreshing authorization token...[/cyan]")
        auto_authenticate()
    app()


if __name__ == "__main__":
    main()

# TODO: Register additional commands as modules are added 