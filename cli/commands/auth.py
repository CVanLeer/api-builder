import typer
from cli.config import save_credentials
from cli.utils.api_client import authenticate_client
from cli.state import state_manager


auth_app = typer.Typer()


@auth_app.command()
def get_token():
    """
    Prompt user for credentials and retrieve a bearer token from /auth/token.
    """
    email = typer.prompt("Email")
    password = typer.prompt("Password", hide_input=True)

    token = authenticate_client(email, password)
    if token:
        state_manager.save_token(token)
        save_credentials(email, password)  # Save credentials for auto-retry
        typer.echo("✅ Access Token Updated")
    else:
        typer.echo("❌ Authentication failed.") 