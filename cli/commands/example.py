import typer

example_app = typer.Typer()

@example_app.command()
def hello(name: str):
    """Say hello."""
    typer.echo(f"Hello, {name}!")  # TODO: Replace with API call later

# TODO: Replace this with a call to the generated API client when ready
# TODO: Add parameter validation, type annotations, and result formatting

def example_command():
    typer.echo("Example command executed.") 