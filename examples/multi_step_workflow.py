#!/usr/bin/env python3
"""
Example: Multi-Step Workflow with Dependency Resolution

This script demonstrates how to:
1. Use API Builder's dependency analyzer
2. Automatically resolve parameter dependencies
3. Execute complex multi-step workflows
4. Handle circular dependencies gracefully

Requirements:
    - Python 3.12+
    - API Builder installed and authenticated
    - OpenAPI spec with endpoint relationships
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.dependency_analyzer import DependencyAnalyzer
from cli.parameter_detector import ParameterDetector
from cli.commands.system import get_dependency_analyzer, execute_endpoint
from cli.context import get_value, save_context
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def load_openapi_spec() -> Dict[str, Any]:
    """
    Load the OpenAPI specification for analysis.
    
    Returns:
        dict: The loaded OpenAPI specification
        
    Raises:
        FileNotFoundError: If the OpenAPI spec file is not found
        json.JSONDecodeError: If the spec file is invalid JSON
    """
    spec_path = Path("openapi/openai.json")
    
    if not spec_path.exists():
        console.print(f"[red]❌ OpenAPI spec not found at {spec_path}[/red]")
        console.print("[yellow]Make sure you have placed your OpenAPI spec in openapi/openai.json[/yellow]")
        raise FileNotFoundError(f"OpenAPI spec not found: {spec_path}")
    
    try:
        with open(spec_path) as f:
            spec = json.load(f)
        console.print("[green]✅ OpenAPI specification loaded[/green]")
        return spec
    except json.JSONDecodeError as e:
        console.print(f"[red]❌ Invalid JSON in OpenAPI spec: {e}[/red]")
        raise


def analyze_endpoint_dependencies(endpoint_path: str) -> List[str]:
    """
    Analyze dependencies for a specific endpoint.
    
    Args:
        endpoint_path: The API endpoint path to analyze
        
    Returns:
        List[str]: List of endpoint paths that this endpoint depends on
    """
    analyzer = get_dependency_analyzer()
    
    # Get the execution plan for this endpoint
    if endpoint_path in analyzer.paths and 'get' in analyzer.paths[endpoint_path]:
        params = analyzer.paths[endpoint_path]['get'].get('parameters', [])
        required_params = [p['name'] for p in params if p.get('required', False)]
        
        execution_plan = analyzer.get_execution_plan(endpoint_path, required_params)
        
        console.print(f"[cyan]Dependency chain for {endpoint_path}:[/cyan]")
        for i, ep in enumerate(execution_plan):
            if i == len(execution_plan) - 1:
                console.print(f"  {i + 1}. [bold]{ep}[/bold] (target endpoint)")
            else:
                console.print(f"  {i + 1}. {ep}")
        
        return execution_plan[:-1]  # All except the target endpoint
    
    return []


def execute_workflow_step(
    endpoint: str, 
    context: Dict[str, Any],
    progress: Optional[Progress] = None,
    task_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Execute a single step in a multi-step workflow.
    
    Args:
        endpoint: The endpoint to call
        context: Current parameter context
        progress: Optional progress tracker
        task_id: Optional progress task ID
        
    Returns:
        dict | None: The API response, or None if failed
    """
    if progress and task_id:
        progress.update(task_id, description=f"Executing {endpoint}...")
    
    analyzer = get_dependency_analyzer()
    
    # Get parameters for this endpoint
    params_info = []
    if endpoint in analyzer.paths and 'get' in analyzer.paths[endpoint]:
        params_info = analyzer.paths[endpoint]['get'].get('parameters', [])
    
    # Build parameters from context
    endpoint_params = {}
    for param in params_info:
        param_name = param['name']
        if param_name in context:
            endpoint_params[param_name] = context[param_name]
        elif not param.get('required', False):
            # Use default value for optional parameters
            endpoint_params[param_name] = param.get('default', '')
    
    # Execute the endpoint
    response = execute_endpoint(endpoint, endpoint_params)
    
    if response:
        console.print(f"[green]✅ Successfully executed {endpoint}[/green]")
        return response
    else:
        console.print(f"[red]❌ Failed to execute {endpoint}[/red]")
        return None


def interactive_parameter_selection(response: Dict[str, Any], param_name: str) -> Optional[str]:
    """
    Let the user interactively select a parameter value from API response.
    
    Args:
        response: The API response containing selectable items
        param_name: The name of the parameter to select
        
    Returns:
        str | None: The selected parameter value
    """
    data = response.get('data', response) if isinstance(response, dict) else response
    
    if not isinstance(data, list) or not data:
        console.print(f"[yellow]⚠️ No selectable items found for {param_name}[/yellow]")
        return None
    
    # Display options in a table
    table = Table(title=f"Select {param_name}")
    table.add_column("#", style="magenta", width=3)
    
    # Determine columns to show
    if isinstance(data[0], dict):
        columns = list(data[0].keys())[:4]  # Show first 4 columns
        for col in columns:
            table.add_column(col, style="cyan")
        
        # Add rows
        for idx, item in enumerate(data[:20]):  # Show first 20 items
            row = [str(idx)] + [str(item.get(col, '')) for col in columns]
            table.add_row(*row)
    else:
        table.add_column("Value", style="cyan")
        for idx, item in enumerate(data[:20]):
            table.add_row(str(idx), str(item))
    
    console.print(table)
    
    if len(data) > 20:
        console.print(f"[dim]... and {len(data) - 20} more items[/dim]")
    
    # Get user selection
    while True:
        try:
            choice = input(f"Select {param_name} (enter row number): ").strip()
            idx = int(choice)
            
            if 0 <= idx < len(data):
                selected_item = data[idx]
                
                # Extract ID from the selected item
                if isinstance(selected_item, dict):
                    # Try common ID field names
                    for id_field in ['id', 'Id', f'{param_name.lower()}', param_name]:
                        if id_field in selected_item:
                            return str(selected_item[id_field])
                    
                    # If no ID field found, use the first field
                    first_key = list(selected_item.keys())[0]
                    return str(selected_item[first_key])
                else:
                    return str(selected_item)
            else:
                console.print(f"[red]Please enter a number between 0 and {len(data) - 1}[/red]")
                
        except ValueError:
            console.print("[red]Please enter a valid number[/red]")
        except KeyboardInterrupt:
            console.print("\n[yellow]Selection cancelled[/yellow]")
            return None


def execute_complex_workflow():
    """
    Execute a complex multi-step workflow demonstrating dependency resolution.
    
    This example shows how to:
    1. Select a target endpoint that requires parameters
    2. Automatically determine dependency chain
    3. Execute each step in the chain
    4. Collect parameter values interactively
    5. Finally execute the target endpoint
    """
    console.print("[bold]Multi-Step Workflow Example[/bold]\n")
    
    try:
        # Load and analyze the API
        spec = load_openapi_spec()
        analyzer = get_dependency_analyzer()
        
        # Show available endpoints that require parameters
        complex_endpoints = []
        for path, methods in analyzer.paths.items():
            if 'get' in methods:
                params = methods['get'].get('parameters', [])
                required_params = [p for p in params if p.get('required', False)]
                if required_params:
                    complex_endpoints.append((path, required_params))
        
        if not complex_endpoints:
            console.print("[yellow]No complex endpoints found in your API spec[/yellow]")
            return
        
        # Display complex endpoints
        table = Table(title="Complex Endpoints (Require Parameters)")
        table.add_column("#", style="magenta", width=3)
        table.add_column("Endpoint", style="cyan")
        table.add_column("Required Parameters", style="yellow")
        
        for idx, (endpoint, params) in enumerate(complex_endpoints[:10]):
            param_names = [p['name'] for p in params]
            table.add_row(str(idx), endpoint, ", ".join(param_names))
        
        console.print(table)
        
        # Let user select an endpoint
        while True:
            try:
                choice = input("Select endpoint to execute (enter number): ").strip()
                idx = int(choice)
                
                if 0 <= idx < len(complex_endpoints):
                    target_endpoint, required_params = complex_endpoints[idx]
                    break
                else:
                    console.print(f"[red]Please enter a number between 0 and {len(complex_endpoints) - 1}[/red]")
            except ValueError:
                console.print("[red]Please enter a valid number[/red]")
            except KeyboardInterrupt:
                console.print("\n[yellow]Cancelled[/yellow]")
                return
        
        console.print(f"\n[cyan]Selected endpoint: {target_endpoint}[/cyan]")
        
        # Analyze dependencies
        param_names = [p['name'] for p in required_params]
        execution_plan = analyzer.get_execution_plan(target_endpoint, param_names)
        
        console.print(f"[yellow]Execution plan ({len(execution_plan)} steps):[/yellow]")
        for i, ep in enumerate(execution_plan):
            console.print(f"  {i + 1}. {ep}")
        
        # Execute the workflow
        context = {}
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            main_task = progress.add_task("Executing workflow...", total=None)
            
            # Execute dependency chain
            for i, endpoint in enumerate(execution_plan[:-1]):  # All except target
                step_response = execute_workflow_step(endpoint, context, progress, main_task)
                
                if not step_response:
                    console.print(f"[red]❌ Workflow failed at step {i + 1}: {endpoint}[/red]")
                    return
                
                # Determine what parameter this step provides
                next_endpoint = execution_plan[i + 1]
                next_params = analyzer.paths[next_endpoint]['get'].get('parameters', [])
                
                for param in next_params:
                    if param.get('required', False) and param['name'] not in context:
                        # This step should provide this parameter
                        param_value = interactive_parameter_selection(step_response, param['name'])
                        if param_value:
                            context[param['name']] = param_value
                            save_context({param['name']: param_value})
                        break
            
            # Execute target endpoint
            progress.update(main_task, description=f"Executing target endpoint: {target_endpoint}")
            final_response = execute_workflow_step(target_endpoint, context, progress, main_task)
            
            if final_response:
                progress.update(main_task, description="✅ Workflow completed successfully!")
                
                # Display results
                console.print(f"\n[bold green]✅ Workflow completed![/bold green]")
                console.print(f"[cyan]Final result from {target_endpoint}:[/cyan]")
                
                # Pretty print the response
                if isinstance(final_response, dict) and 'data' in final_response:
                    data = final_response['data']
                    if isinstance(data, list):
                        console.print(f"[green]Retrieved {len(data)} items[/green]")
                    console.print(json.dumps(data if isinstance(data, (list, dict)) else final_response, indent=2))
                else:
                    console.print(json.dumps(final_response, indent=2))
                
                # Save results
                filename = f"workflow_result_{target_endpoint.replace('/', '_')}.json"
                with open(filename, 'w') as f:
                    json.dump(final_response, f, indent=2)
                console.print(f"[dim]Results saved to {filename}[/dim]")
                
            else:
                console.print("[red]❌ Final step failed[/red]")
    
    except Exception as e:
        console.print(f"[red]❌ Workflow error: {e}[/red]")


def main():
    """Main function to run the multi-step workflow example."""
    try:
        execute_complex_workflow()
    except KeyboardInterrupt:
        console.print("\n[yellow]Workflow cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)