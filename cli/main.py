import typer
from cli.commands import example
from cli.commands import auth
from cli.commands import system


app = typer.Typer(help="CLI for interacting with the generated API client.")

app.add_typer(auth.auth_app, name="auth")
app.add_typer(example.example_app, name="example")
app.add_typer(system.system_app, name="system")


if __name__ == "__main__":
    app()

# TODO: Register additional commands as modules are added 