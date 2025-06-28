import typer
import importlib
import click
from cli.context import get_value, save_context
from pathlib import Path
import json
import logging
from datetime import datetime

system_app = typer.Typer()
ENDPOINTS_ROOT = Path("cli/endpoints/gettattle")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def list_available_endpoints() -> dict:
    spec_path = Path("openapi/openai.json")
    with open(spec_path) as f:
        openapi = json.load(f)
    paths = openapi.get("paths", {})
    sorted_paths = sorted(
        paths.items(),
        key=lambda p: len(p[1].get("get", {}).get("parameters", []))
    )
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


def extract_date_param_formats(openapi):
    formats = {}
    for path, methods in openapi.get("paths", {}).items():
        if "get" not in methods:
            continue
        parameters = methods["get"].get("parameters", [])
        for param in parameters:
            name = param.get("name")
            schema = param.get("schema", {})
            fmt = schema.get("format", "")
            desc = param.get("description", "")
            if (
                "date" in name.lower() or
                "date" in fmt or
                "date" in desc.lower()
            ):
                if "time" in fmt:
                    formats[name] = "%Y-%m-%dT%H:%M:%S"
                else:
                    formats[name] = "%Y-%m-%d"
    return formats


def normalize_date_input(raw_input: str, required_format: str) -> str:
    try:
        parsed = datetime.strptime(raw_input, "%m-%d-%Y")
        return parsed.strftime(required_format)
    except ValueError:
        typer.echo("❌ Invalid date format. Expected MM-DD-YYYY")
        raise


def resolve_param_value(name, openapi, date_formats):
    if name.lower() == "page":
        return 1
    if name.lower() in ("pagesize", "limit"):
        return 50

    val = get_value(name)
    if val:
        return val

    if name in date_formats:
        raw_input = typer.prompt(f"Enter {name} (MM-DD-YYYY)")
        formatted = normalize_date_input(raw_input, date_formats[name])
        save_context({name: formatted})
        return formatted

    resolver_map = {
        "merchantId": "/merchants",
        "locationId": "/locations",
        "groupId": "/groups"
    }

    fallback_path = resolver_map.get(name)
    if not fallback_path:
        manual = typer.prompt(f"Enter value for required param '{name}'")
        save_context({name: manual})
        return manual

    try:
        module_name = fallback_path.strip("/").split("/")[0].replace("-", "_")
        func_name = fallback_path.strip("/").replace("/", "_") \
            .replace("{", "").replace("}", "")
        mod = importlib.import_module(f"cli.endpoints.gettattle.{module_name}")
        fn = getattr(mod, func_name)

        typer.echo(f"🔁 Resolving '{name}' via {fallback_path}")
        result = fn()

        data = result.get("data") if isinstance(result, dict) else result
        if isinstance(data, list) and data:
            first = data[0]
            if name in first:
                selected = str(first[name])
            elif "id" in first:
                selected = str(first["id"])
            else:
                selected = str(next(iter(first.values())))

            typer.echo(f"✅ Selected {name}: {selected}")
            logger.info(f"{name} found: {selected}")
            if typer.confirm(f"Store '{name}' for future use?", default=True):
                save_context({name: selected})
            return selected

    except Exception as e:
        typer.echo(f"⚠️  Auto-resolution failed for '{name}': {e}")

    manual = typer.prompt(f"Enter value for required param '{name}'")
    save_context({name: manual})
    return manual


@system_app.command()
def query_api(endpoint: str = typer.Argument(None, help="API endpoint path (e.g., /merchants, /locations)")):
    spec_path = Path("openapi/openai.json")
    with open(spec_path) as f:
        openapi = json.load(f)

    date_formats = extract_date_param_formats(openapi)

    endpoints = list_available_endpoints()
    
    if endpoint:
        if endpoint not in endpoints:
            typer.echo(f"❌ Invalid endpoint: {endpoint}")
            typer.echo(f"Available endpoints: {', '.join(endpoints.keys())}")
            raise typer.Exit(1)
        path = endpoint
    else:
        path = typer.prompt(
            "Which endpoint?",
            type=click.Choice(list(endpoints.keys()))
        )

    method_data = endpoints[path]
    required_params = get_param_names(method_data)
    args = {
        name: resolve_param_value(name, openapi, date_formats)
        for name in required_params
    }

    module_name = path.strip("/").split("/")[0].replace("-", "_")
    func_name = path.strip("/").replace("/", "_") \
        .replace("{", "").replace("}", "")
    try:
        mod = importlib.import_module(
            f"cli.endpoints.gettattle.{module_name}"
        )
        fn = getattr(mod, func_name)
    except Exception as e:
        typer.echo(f"❌ Cannot import {func_name}: {e}")
        return

    results = []
    page = int(args.get("Page", 1))
    while True:
        args["Page"] = page
        response = fn(args)
        data = response.get("data") \
            if isinstance(response, dict) else response
        if isinstance(data, list):
            results.extend(data)
        else:
            results.append(data)
        if not response.get("hasNextPage"):
            break
        page += 1

    typer.echo(json.dumps(results, indent=2))