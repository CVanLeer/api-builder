import typer
import importlib
from cli.context import get_value, save_context
from cli.dependency_analyzer import DependencyAnalyzer
from cli.parameter_detector import ParameterDetector, ParameterType
from pathlib import Path
import json
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm

system_app = typer.Typer()
console = Console()
ENDPOINTS_ROOT = Path("cli/endpoints/gettattle")

# Cache for dependency analysis
_dependency_cache = {}


def get_dependency_analyzer() -> DependencyAnalyzer:
    """Get or create a cached dependency analyzer"""
    if 'analyzer' not in _dependency_cache:
        spec_path = Path("openapi/openai.json")
        with open(spec_path) as f:
            openapi = json.load(f)
        _dependency_cache['analyzer'] = DependencyAnalyzer(openapi)
        _dependency_cache['analyzer'].analyze_parameters()
    return _dependency_cache['analyzer']


def get_parameter_detector() -> ParameterDetector:
    """Get or create a cached parameter detector"""
    if 'detector' not in _dependency_cache:
        _dependency_cache['detector'] = ParameterDetector()
    return _dependency_cache['detector']


def execute_endpoint(endpoint: str, params: dict) -> dict | None:
    """Execute an endpoint with given parameters"""
    module_name = endpoint.strip("/").split("/")[0].replace("-", "_")
    func_name = (
        endpoint.strip("/").replace("/", "_")
        .replace("{", "").replace("}", "")
    )
    try:
        mod = importlib.import_module(f"cli.endpoints.gettattle.{module_name}")
        fn = getattr(mod, func_name)
        return fn(params)
    except Exception as e:
        console.print(f"[red]❌ Error calling {endpoint}: {e}[/red]")
        return None


def rank_provider(endpoint: str, analyzer: DependencyAnalyzer) -> int:
    """Lower score is better for provider endpoints"""
    score = 0
    if '{' in endpoint:
        score += 10
    if endpoint in analyzer.paths and 'get' in analyzer.paths[endpoint]:
        params = analyzer.paths[endpoint]['get'].get('parameters', [])
        required_count = sum(1 for p in params if p.get('required', False))
        score += required_count
    return score


def select_from_response(response, param_name: str, endpoint: str) -> object | None:
    """Interactive selection from API response"""
    detector = get_parameter_detector()
    data = response
    if isinstance(response, dict):
        data = response.get('data', response)
    if isinstance(data, list) and data:
        table = Table(title=f"Select {param_name} from {endpoint}")
        if isinstance(data[0], dict):
            columns = list(data[0].keys())[:5]
            for col in columns:
                table.add_column(col)
            for idx, item in enumerate(data[:20]):
                row = [str(item.get(col, '')) for col in columns]
                table.add_row(*row)
            console.print(table)
            if len(data) > 20:
                console.print(
                    f"[yellow]Showing first 20 of {len(data)} items[/yellow]"
                )
            while True:
                max_idx = min(len(data) - 1, 19)
                row_prompt = f"Enter row number (0-{max_idx})"
                choice = Prompt.ask(
                    row_prompt,
                    default="0"
                )
                try:
                    idx = int(choice)
                    if 0 <= idx < len(data):
                        selected_item = data[idx]
                        value = detector.extract_id_from_response(
                            selected_item, param_name
                        )
                        if value:
                            return value
                        else:
                            console.print(
                                f"[red]Could not extract {param_name} "
                                "from selection[/red]"
                            )
                            return None
                except ValueError:
                    console.print(
                        "[red]Please enter a valid number[/red]"
                    )
        else:
            for idx, item in enumerate(data[:20]):
                console.print(f"{idx}: {item}")
            choice = Prompt.ask("Select index", default="0")
            try:
                return data[int(choice)]
            except Exception:
                return data[0]
    return detector.extract_id_from_response(response, param_name)


def resolve_parameter_with_dependency(
    param_name: str,
    param_info: dict,
    analyzer: DependencyAnalyzer,
    endpoint: str,
    progress: Progress | None = None,
    task_id: int | None = None
) -> object | None:
    """Resolve a parameter using dependency analysis"""
    detector = get_parameter_detector()
    cached_value = get_value(param_name)
    if cached_value:
        if progress and task_id:
            progress.update(
                task_id,
                description=(
                    f"✅ Using cached {param_name}: {cached_value}"
                )
            )
        return cached_value
    param_type_info = detector.detect_parameter_type(param_name, param_info)
    if param_type_info.type == ParameterType.PAGINATION:
        if param_name.lower() == "page":
            return 1
        if param_name.lower() in ("pagesize", "limit", "size"):
            return 50
    if param_type_info.type == ParameterType.BOOLEAN:
        return Confirm.ask(f"Value for {param_name}")
    if param_type_info.type == ParameterType.ENUM:
        return Prompt.ask(
            f"Select {param_name}",
            choices=param_type_info.enum_values
        )
    providers = analyzer.find_parameter_providers(param_name)
    if providers:
        # Sort by simplicity
        providers.sort(key=lambda p: rank_provider(p, analyzer))
        # Special case for merchantId - prefer /merchants
        if param_name.lower() == 'merchantid' and '/merchants' in providers:
            selected_provider = '/merchants'
        else:
            selected_provider = providers[0]
    else:
        if progress and task_id:
            progress.update(
                task_id,
                description=(
                    f"⚠️  No provider found for {param_name}"
                )
            )
        manual_value = Prompt.ask(f"Enter value for {param_name}")
        save_context({param_name: manual_value})
        return manual_value
    if progress and task_id:
        progress.update(
            task_id,
            description=(
                f"🔗 Fetching {param_name} from {selected_provider}..."
            )
        )
    console.print(
        f"\n[cyan]Calling {selected_provider} to get {param_name}...[/cyan]"
    )
    # Recursively resolve parameters for the provider endpoint
    provider_params = {}
    provider_params_info = []
    if (
        selected_provider in analyzer.paths and
        'get' in analyzer.paths[selected_provider]
    ):
        provider_params_info = analyzer.paths[selected_provider]['get'].get(
            'parameters', []
        )
    for dep_param in provider_params_info:
        dep_param_name = dep_param['name']
        if dep_param.get('required', False):
            dep_value = resolve_parameter_with_dependency(
                dep_param_name,
                dep_param,
                analyzer,
                selected_provider,
                progress,
                task_id
            )
            if dep_value is not None:
                provider_params[dep_param_name] = dep_value
    response = execute_endpoint(selected_provider, provider_params)
    if response:
        value = select_from_response(response, param_name, selected_provider)
        if value is not None:
            save_context({param_name: value})
            if progress and task_id:
                progress.update(
                    task_id,
                    description=(
                        f"✅ Resolved {param_name}: {value}"
                    )
                )
            return value
    console.print(f"[yellow]Could not auto-resolve {param_name}[/yellow]")
    manual_value = Prompt.ask(f"Enter value for {param_name}")
    save_context({param_name: manual_value})
    return manual_value


@system_app.command()
def query_api():
    """Execute an API endpoint with automatic dependency resolution"""
    analyzer = get_dependency_analyzer()
    # Build endpoints dict from analyzer.paths
    endpoints = {}
    for path, methods in analyzer.paths.items():
        if 'get' in methods:
            endpoints[path] = {
                'method': 'get',
                'summary': methods['get'].get('summary', ''),
                'parameters': methods['get'].get('parameters', [])
            }
    sorted_endpoints = sorted(
        endpoints.items(),
        key=lambda x: len(x[1].get('parameters', []))
    )
    table = Table(title="Available API Endpoints")
    table.add_column("#", style="magenta")
    table.add_column("Endpoint", style="cyan")
    table.add_column("Method", style="green")
    table.add_column("Summary", style="white")
    table.add_column("Required Params", style="yellow")
    endpoint_list = []
    for idx, (endpoint, details) in enumerate(sorted_endpoints):
        params = [
            p['name'] for p in details.get('parameters', [])
            if p.get('required', False)
        ]
        table.add_row(
            str(idx),
            endpoint,
            'GET',
            details.get('summary', 'No description')[:50],
            ', '.join(params) if params else 'None'
        )
        endpoint_list.append(endpoint)
    console.print(table)
    endpoint_idx = Prompt.ask(
        "Select endpoint (enter number)",
        choices=[str(i) for i in range(len(endpoint_list))]
    )
    selected_endpoint = endpoint_list[int(endpoint_idx)]
    required_param_names = [
        p['name'] for p in endpoints[selected_endpoint].get('parameters', [])
        if p.get('required', False)
    ]
    execution_plan = analyzer.get_execution_plan(
        selected_endpoint, required_param_names
    )
    if len(execution_plan) > 1:
        console.print("[yellow]Dependency chain:[/yellow]")
        for idx, endpoint in enumerate(execution_plan[:-1]):
            next_ep = execution_plan[idx + 1]
            console.print(
                f"  {idx + 1}. {endpoint} -> {next_ep}"
            )
    
    # Collect parameters OUTSIDE the Progress context
    endpoint_params = {}
    param_defs = endpoints[selected_endpoint].get('parameters', [])
    # Collect parameter values: prefer stored, then default
    for param in param_defs:
        param_name = param['name']
        value = get_value(param_name)
        if value is None:
            if param.get('required', False):
                # Do not pass progress/main_task here to avoid
                # progress bar before approval
                value = resolve_parameter_with_dependency(
                    param_name,
                    param,
                    analyzer,
                    selected_endpoint
                )
            else:
                value = param.get('default', '')
        if value is not None:
            endpoint_params[param_name] = value

    # Show all params and ask for approval BEFORE any progress bar or execution
    console.print("\n[bold]Parameters to be used:[/bold]")
    param_table = Table("Parameter", "Value")
    for k, v in endpoint_params.items():
        param_table.add_row(k, str(v))
    console.print(param_table)

    # Approve all prompt
    approve_all_prompt = (
        "Approve All? Y/N (type all to approve all): "
    )
    param_keys = list(endpoint_params.keys())
    approved_params = {}
    approve_all = False
    
    while True:
        resp = Prompt.ask(approve_all_prompt, default="Y").strip().lower()
        print(f"[DEBUG] User input for approve all: '{resp}'")  # Debug print
        if resp in ("y", "yes", "all", ""):
            approved_params = endpoint_params.copy()
            break
        elif resp in ("n", "no"):
            # enter per-parameter approval loop
            i = 0
            while i < len(param_keys):
                k = param_keys[i]
                v = endpoint_params[k]
                if approve_all:
                    approved_params[k] = v
                    i += 1
                    continue
                approve_prompt = (
                    f"Approve {k}={v}? (Y/N, or 'all' to approve all): "
                )
                resp2 = Prompt.ask(
                    approve_prompt,
                    default="Y"
                ).strip().lower()
                print(
                    f"[DEBUG] User input for {k}: '{resp2}'"
                )  # Debug print
                if resp2 == "all":
                    approve_all = True
                    approved_params[k] = v
                    i += 1
                    continue
                if resp2 in ("y", "yes", ""):
                    approved_params[k] = v
                    i += 1
                elif resp2 in ("n", "no"):
                    # Try to get type/format from OpenAPI param definition
                    param_def = next(
                        (p for p in param_defs if p["name"] == k), None
                    )
                    param_type = param_def.get("type") if param_def else "string"
                    param_format = param_def.get("format") if param_def else ""
                    type_str = param_type
                    if param_format:
                        type_str += f" ({param_format})"
                    update_prompt = f"Updated {k} [{type_str}]: "
                    new_val = Prompt.ask(
                        update_prompt,
                        default=str(v)
                    )
                    endpoint_params[k] = new_val
                    # Do not increment i, re-approve this param
                else:
                    print(
                        f"[DEBUG] Invalid input for {k}: '{resp2}'"
                    )
                    continue  # re-prompt for this param
            break
        else:
            print(f"[DEBUG] Invalid input for approve all: '{resp}'")
            continue  # re-prompt for approve all

    # Final confirmation
    console.print("\n[bold]Final parameters to be used:[/bold]")
    final_table = Table("Parameter", "Value")
    for k, v in approved_params.items():
        final_table.add_row(k, str(v))
    console.print(final_table)
    if not Confirm.ask("Proceed with these parameters?"):
        console.print("[red]Aborted by user.[/red]")
        return

    # Only now start the progress bar and execution
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        main_task = progress.add_task(
            f"Resolving parameters for {selected_endpoint}...",
            total=None
        )
        progress.update(main_task, description="Executing endpoint...")
        all_results = []
        page = approved_params.get('Page', approved_params.get('page', 1))
        has_more = True
        while has_more:
            if 'Page' in approved_params:
                approved_params['Page'] = page
            elif 'page' in approved_params:
                approved_params['page'] = page
            progress.update(
                main_task,
                description=(
                    f"Fetching page {page}..."
                )
            )
            response = execute_endpoint(selected_endpoint, approved_params)
            if response:
                if isinstance(response, dict):
                    data = response.get('data', response)
                    if isinstance(data, list):
                        all_results.extend(data)
                    else:
                        all_results.append(data)
                    has_more = response.get('hasNextPage', False)
                    if not has_more:
                        break
                    page += 1
                else:
                    all_results = response
                    has_more = False
            else:
                break
        progress.update(main_task, description="✅ Complete!")
    console.print(
        f"\n[green]Results ({len(all_results)} items):[green]"
    )
    console.print(json.dumps(all_results, indent=2))
    if Confirm.ask("Save results to file?"):
        filename = Prompt.ask("Filename", default="results.json")
        with open(filename, 'w') as f:
            json.dump(all_results, f, indent=2)
        console.print(f"[green]✅ Saved to {filename}[/green]")