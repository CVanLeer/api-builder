import typer
from cli.context import (
    get_value, save_context, save_command_to_history,
    get_recent_commands, replay_command
)
from cli.dependency_analyzer import DependencyAnalyzer
from cli.parameter_detector import ParameterDetector, ParameterType
from pathlib import Path
import json
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from datetime import datetime, timedelta
import os
from cli.utils.api_client import get_client

system_app = typer.Typer(
    help="⚙️ System commands for API exploration and workflow management",
    rich_markup_mode="rich"
)
console = Console()
ENDPOINTS_ROOT = Path("cli/endpoints/gettattle")

# Cache for dependency analysis
_dependency_cache = {}


def get_dependency_analyzer() -> DependencyAnalyzer:
    """
    Get or create a cached dependency analyzer instance.

    This function implements a singleton pattern to ensure only one
    DependencyAnalyzer instance is created per session. The analyzer
    processes the OpenAPI specification to build dependency graphs.

    Returns:
        DependencyAnalyzer: Cached analyzer instance with processed
            parameter dependencies

    Raises:
        FileNotFoundError: If openapi/openai.json is not found
        json.JSONDecodeError: If the OpenAPI spec is invalid JSON

    Example:
        >>> analyzer = get_dependency_analyzer()
        >>> providers = analyzer.find_parameter_providers('merchantId')
        >>> print(providers)
        ['/merchants', '/merchant-details']
    """
    if 'analyzer' not in _dependency_cache:
        spec_path = Path("openapi/openai.json")
        with open(spec_path) as f:
            openapi = json.load(f)
        _dependency_cache['analyzer'] = DependencyAnalyzer(openapi)
        _dependency_cache['analyzer'].analyze_parameters()
    return _dependency_cache['analyzer']


def get_parameter_detector() -> ParameterDetector:
    """
    Get or create a cached parameter detector instance.

    This function provides a singleton ParameterDetector that analyzes
    parameter names and types to provide intelligent type detection
    and value suggestions.

    Returns:
        ParameterDetector: Cached detector instance for parameter analysis

    Example:
        >>> detector = get_parameter_detector()
        >>> param_info = detector.detect_parameter_type('merchantId', {})
        >>> print(param_info.type)
        ParameterType.FOREIGN_KEY
    """
    if 'detector' not in _dependency_cache:
        _dependency_cache['detector'] = ParameterDetector()
    return _dependency_cache['detector']


def execute_endpoint(endpoint: str, params: dict) -> dict | None:
    """
    Execute an API endpoint with the generated client.

    This function maps endpoint paths to the appropriate API client methods
    and executes them with the provided parameters. It handles errors
    gracefully and provides user feedback.

    Args:
        endpoint: The API endpoint path (e.g., '/merchants', '/locations')
        params: Dictionary of parameters to pass to the endpoint

    Returns:
        dict | None: The API response data, or None if the call failed

    Example:
        >>> result = execute_endpoint('/merchants', {'page': 1})
        >>> print(result['data'][0]['name'])
        'Example Merchant'

    Note:
        - Unmapped endpoints will show an error message
        - Network errors are caught and displayed to the user
        - All API calls use the stored authentication token
    """
    try:
        client = get_client()
        # Map endpoint paths to API client methods
        endpoint_mapping = {
            "/merchants": lambda: client.merchants.get_merchants.sync(**params),
            "/locations": lambda: client.locations.get_locations.sync(**params),
            "/groups": lambda: client.groups.get_groups.sync(**params),
            # ... add all other endpoints as needed
        }
        if endpoint in endpoint_mapping:
            return endpoint_mapping[endpoint]()
        else:
            console.print(
                f"[red]❌ Endpoint {endpoint} not implemented in client mapping[/red]"
            )
            console.print(
                "[yellow]💡 Try regenerating the API client: python scripts/regen_client.py[/yellow]"
            )
            return None
    except Exception as e:
        console.print(f"[red]❌ Error calling {endpoint}: {e}[/red]")
        console.print("[yellow]💡 Check your authentication: python cli/main.py auth get-token[/yellow]")
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
    task_id: int | None = None,
    _resolving_stack: set = None
) -> object | None:
    """Resolve a parameter using dependency analysis"""
    # Initialize recursion detection stack
    if _resolving_stack is None:
        _resolving_stack = set()
    
    # Check for circular dependency
    if param_name in _resolving_stack:
        console.print(f"[yellow]⚠️ Circular dependency detected for {param_name}[/yellow]")
        console.print(f"[dim]💡 This happens when endpoints reference each other. Providing manual input.[/dim]")
        manual_value = Prompt.ask(f"Enter value for {param_name}")
        save_context({param_name: manual_value})
        return manual_value
    
    # Add current parameter to resolving stack
    _resolving_stack.add(param_name)
    
    try:
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
                        f"⚠️ No provider found for {param_name}"
                    )
                )
            console.print(f"[yellow]⚠️ No automatic provider found for '{param_name}'[/yellow]")
            console.print(f"[dim]💡 This parameter needs to be provided manually.[/dim]")
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
                    task_id,
                    _resolving_stack
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
    finally:
        # Clean up: remove parameter from resolving stack
        _resolving_stack.discard(param_name)


def set_default_dates():
    """Set default date parameters in context"""
    defaults = {
        'StartDateExperiencedLocal': (
            datetime.now() - timedelta(days=7)
        ).strftime('%Y-%m-%d'),
        'EndDateExperiencedLocal': datetime.now().strftime('%Y-%m-%d'),
        'StartDate': (
            datetime.now() - timedelta(days=7)
        ).strftime('%Y-%m-%d'),
        'EndDate': datetime.now().strftime('%Y-%m-%d'),
        'StartDateUtc': (
            datetime.now() - timedelta(days=7)
        ).strftime('%Y-%m-%d'),
        'EndDateUtc': datetime.now().strftime('%Y-%m-%d'),
        'ExperienceStartDate': (
            datetime.now() - timedelta(days=7)
        ).strftime('%Y-%m-%d'),
        'ExperienceEndDate': datetime.now().strftime('%Y-%m-%d'),
        'CreatedStartDate': (
            datetime.now() - timedelta(days=7)
        ).strftime('%Y-%m-%d'),
        'CreatedEndDate': datetime.now().strftime('%Y-%m-%d'),
    }
    save_context(defaults)
    console.print("[green]✅ Default dates set in context[/green]")


@system_app.command()
def query_api():
    """
    🔍 Interactive API explorer with automatic dependency resolution.
    
    This command shows all available endpoints, lets you select one to call,
    automatically resolves parameter dependencies, and executes the API call.
    Perfect for discovering what data is available in your API.
    """
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
        page = int(approved_params.get('Page', approved_params.get('page', 1)))
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
        
        # Save successful command to history
        save_command_to_history(selected_endpoint, approved_params, success=bool(all_results))
        progress.update(main_task, description="✅ Complete!")
    console.print(
        f"\n[green]Results ({len(all_results)} items):[green]"
    )
    console.print(json.dumps(all_results, indent=2))
    save_prompt = "Save results to file? [y/n/clean]: "
    resp = Prompt.ask(save_prompt, default="n").strip().lower()
    if resp in ("y", "yes"):
        filename = Prompt.ask("Filename", default="results.json")
        with open(filename, 'w') as f:
            json.dump(all_results, f, indent=2)
        console.print(f"[green]✅ Saved to {filename}[/green]")
    elif resp == "clean":
        cleaned = clean_json_results(all_results)
        console.print("[cyan]Showing cleaned results:[/cyan]")
        console.print(json.dumps(cleaned, indent=2))
        filename = Prompt.ask(
            "Filename for cleaned results",
            default="results_clean.json"
        )
        with open(filename, 'w') as f:
            json.dump(cleaned, f, indent=2)
        console.print(f"[green]✅ Cleaned results saved to {filename}[/green]")


@system_app.command()
def set_defaults():
    """
    📅 Set default date ranges and common parameters.
    
    Pre-populates context with default values for date parameters like
    startDate, endDate, etc. Saves time when making repeated API calls
    with time-series data.
    """
    set_default_dates()

@system_app.command()
def history(limit: int = typer.Option(10, help="Number of recent commands to show")):
    """
    📜 Show recent command history with status and parameters.
    
    Displays a table of recent API calls with their parameters and success status.
    Use this to track what you've called and find commands to replay.
    """
    recent = get_recent_commands(limit)
    
    if not recent:
        console.print("[yellow]No command history found[/yellow]")
        return
    
    table = Table(title="Recent Commands")
    table.add_column("#", style="magenta", width=3)
    table.add_column("Timestamp", style="blue", width=20)
    table.add_column("Endpoint", style="cyan", width=30)
    table.add_column("Parameters", style="white", width=50)
    table.add_column("Status", style="green", width=10)
    
    for idx, cmd in enumerate(recent):
        timestamp = cmd['timestamp'][:19].replace('T', ' ')  # Format timestamp
        status = "✅" if cmd['success'] else "❌"
        params_str = ", ".join([f"{k}={v}" for k, v in cmd['parameters'].items() if v])
        if len(params_str) > 47:
            params_str = params_str[:44] + "..."
        
        table.add_row(
            str(idx),
            timestamp,
            cmd['endpoint'],
            params_str,
            status
        )
    
    console.print(table)
    console.print(f"\n[dim]Use 'replay <number>' to run a command again[/dim]")

@system_app.command()
def replay(index: int = typer.Argument(help="Index number from history command")):
    """
    🔄 Replay a previous command from history.
    
    Re-executes a command from your history with the same parameters.
    Useful for repeating successful API calls or testing consistency.
    Use 'history' command first to see available commands.
    """
    cmd = replay_command(index)
    
    if not cmd:
        console.print(f"[red]No command found at index {index}[/red]")
        return
    
    console.print(f"[cyan]Replaying command:[/cyan] {cmd['endpoint']}")
    console.print(f"[dim]Original timestamp:[/dim] {cmd['timestamp']}")
    
    # Show parameters
    param_table = Table("Parameter", "Value")
    for k, v in cmd['parameters'].items():
        param_table.add_row(k, str(v))
    console.print(param_table)
    
    if not Confirm.ask("Execute this command?"):
        console.print("[yellow]Command cancelled[/yellow]")
        return
    
    # Execute the command
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        main_task = progress.add_task(f"Executing {cmd['endpoint']}...", total=None)
        response = execute_endpoint(cmd['endpoint'], cmd['parameters'])
        
        if response:
            console.print(f"\n[green]✅ Command executed successfully[/green]")
            console.print(json.dumps(response, indent=2))
            
            # Save to history again
            save_command_to_history(cmd['endpoint'], cmd['parameters'], success=True)
        else:
            console.print(f"\n[red]❌ Command failed[/red]")
            save_command_to_history(cmd['endpoint'], cmd['parameters'], success=False)

def clean_json_results(results):
    """Clean JSON results by replacing ID fields with labels from lookup files."""
    # Load locations lookup
    locations_path = os.path.join(
        os.path.dirname(__file__), '../../locations.json'
    )
    try:
        with open(locations_path, 'r') as f:
            locations = {
                str(loc['id']): loc['label']
                for loc in json.load(f)
            }
    except Exception:
        locations = {}

    def clean_item(item):
        if isinstance(item, dict):
            new_item = {}
            for k, v in item.items():
                # Replace locationId with location label
                if k == 'locationId' and str(v) in locations:
                    new_item['location'] = locations[str(v)]
                elif isinstance(v, (dict, list)):
                    new_item[k] = clean_item(v)
                else:
                    new_item[k] = v
            return new_item
        elif isinstance(item, list):
            return [clean_item(i) for i in item]
        else:
            return item
    return clean_item(results)