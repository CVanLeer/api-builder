### file: cli/commands/system.py

import typer
import importlib
import click
from cli.context import get_value, save_context
from pathlib import Path
import json

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


def get_param_names(method_data):
    return [
        p["name"]
        for p in method_data.get("parameters", [])
        if p.get("required", False)
    ]


def resolve_param_value(name, openapi):
    # Pagination defaults
    if name.lower() == "page":
        return 1
    if name.lower() in ("pagesize", "limit"):
        return 50

    val = get_value(name)
    if val:
        return val

    # Try to auto-resolve via known endpoints
    for path, methods in openapi.get("paths", {}).items():
        if "get" not in methods:
            continue
        response = methods["get"].get("responses", {}).get("200", {})
        example = response.get("content", {}).get("application/json", {}).get("example", {})
        if name in example:
            module_name = path.strip("/").split("/")[0].replace("-", "_")
            func_name = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
            try:
                mod = importlib.import_module(f"cli.endpoints.gettattle.{module_name}")
                fn = getattr(mod, func_name)
                typer.echo(f"🔁 Fetching '{name}' via: {path}")
                result = fn()
                if isinstance(result, list) and result:
                    options = [str(item[name]) for item in result if name in item]
                    chosen = typer.prompt(f"Select {name}", type=click.Choice(options))
                    save_context({name: chosen})
                    return chosen
            except Exception as e:
                typer.echo(f"⚠️  Could not auto-fetch {name}: {e}")

    manual = typer.prompt(f"Enter value for required param '{name}'")
    save_context({name: manual})
    return manual


@system_app.command()
def query_api():
    spec_path = Path("openapi/openai.json")
    with open(spec_path) as f:
        openapi = json.load(f)

    endpoints = list_available_endpoints()
    path = typer.prompt("Which endpoint?", type=click.Choice(list(endpoints.keys())))

    method_data = endpoints[path]
    required_params = get_param_names(method_data)
    args = {name: resolve_param_value(name, openapi) for name in required_params}

    # Setup module/function
    module_name = path.strip("/").split("/")[0].replace("-", "_")
    func_name = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    try:
        mod = importlib.import_module(f"cli.endpoints.gettattle.{module_name}")
        fn = getattr(mod, func_name)
    except Exception as e:
        typer.echo(f"❌ Cannot import {func_name}: {e}")
        return

    # Pagination loop
    results = []
    page = int(args.get("Page", 1))
    while True:
        args["Page"] = page
        response = fn(args)
        data = response.get("data") or response
        if isinstance(data, list):
            results.extend(data)
        else:
            results.append(data)

        # Exit if no pagination
        if not response.get("hasNextPage"):
            break
        page += 1

    typer.echo(json.dumps(results, indent=2))