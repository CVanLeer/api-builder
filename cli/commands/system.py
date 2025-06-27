import typer
import importlib
from cli.context import get_value, save_context
from pathlib import Path
import json
import click


system_app = typer.Typer()

ENDPOINTS_ROOT = Path("cli/endpoints/gettattle")

def list_available_endpoints() -> dict:
    spec_path = Path("openapi/openai.json")
    with open(spec_path) as f:
        openapi = json.load(f)
    paths = openapi.get("paths", {})
    sorted_paths = sorted(paths.items(), key=lambda p: len(p[1].get("get", {}).get("parameters", [])))
    return {
        path: method["get"]
        for path, method in sorted_paths
        if "get" in method
    }

def prompt_for_params(params):
    final = {}
    for p in params:
        name = p["name"]
        required = p.get("required", False)
        val = get_value(name)
        if val:
            final[name] = val
        elif required:
            final[name] = typer.prompt(f"Enter value for required param '{name}'")
            if typer.confirm(f"Store '{name}' for future use?", default=True):
                save_context({name: final[name]})
    return final

@system_app.command()
def query_api():
    endpoints = list_available_endpoints()
    choices = list(endpoints.keys())
    path = typer.prompt("Which endpoint?", type=click.Choice(choices))
 

    module_name = path.strip("/").split("/")[0].replace("-", "_")
    function_name = path.strip("/").replace("/", "_")

    try:
        mod = importlib.import_module(f"cli.endpoints.gettattle.{module_name}")
        func = getattr(mod, function_name)
    except Exception as e:
        typer.echo(f"❌ Cannot import: {e}")
        return

    params = endpoints[path]["parameters"]
    args = prompt_for_params(params)
    try:
        result = func(args)
        typer.echo(json.dumps(result, indent=2))
    except Exception as e:
        typer.echo(f"❌ Error running endpoint: {e}") 