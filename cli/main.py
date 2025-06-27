import typer
from cli.commands import example

app = typer.Typer(help="CLI for interacting with the generated API client.")

# Register subcommands
app.add_typer(example.example_app, name="example")

if __name__ == "__main__":
    app()

# TODO: Register additional commands as modules are added 