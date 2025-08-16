import typer
from cli.config import save_credentials
from cli.utils.api_client import authenticate_client
from cli.state import state_manager


auth_app = typer.Typer(
    help="🔐 Authentication commands for API access",
    rich_markup_mode="rich"
)


@auth_app.command()
def get_token():
    """
    Interactively authenticate with the API and store credentials.

    This command prompts the user for email and password credentials,
    authenticates with the API's /auth/token endpoint, and stores both
    the retrieved bearer token and credentials for future automatic
    re-authentication.

    The credentials are securely stored and used for automatic token
    refresh when the current token expires (after 24 hours).

    Args:
        None (interactive prompts)

    Example:
        $ python cli/main.py auth get-token
        Email: user@example.com
        Password: [hidden]
        ✅ Access Token Updated

    Note:
        - Password input is hidden for security
        - Credentials are encrypted before storage
        - Failed authentication will display an error message
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