import typer
import requests
from cli.config import settings, save_token, save_credentials

auth_app = typer.Typer()

@auth_app.command()
def get_token():
    """
    Prompt user for credentials and retrieve a bearer token from /auth/token.
    """
    email = typer.prompt("Email")
    password = typer.prompt("Password", hide_input=True)

    url = f"{settings.api_base_url}/auth/token"
    payload = {"email": email, "password": password}

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        token = response.json().get("accessToken")
        save_token(token)
        save_credentials(email, password)  # Save credentials for auto-retry
        typer.echo("✅ Access Token Updated")
    else:
        typer.echo(f"❌ Failed to authenticate: {response.status_code} - {response.text}") 