#!/usr/bin/env python3
"""
Interactive Terminal for API Central
====================================

An interactive terminal session that lists and allows testing of all available
functions and commands in the api-central project.
"""

import os
import sys
import subprocess
from typing import List, Dict, Tuple
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint

console = Console()

# Define available commands with their descriptions and invocation methods
COMMANDS = {
    "Authentication": [
        {
            "name": "Get Token",
            "command": "python -m cli.main auth get-token",
            "description": "Authenticate and retrieve a bearer token",
            "category": "auth"
        }
    ],
    "API Queries": [
        {
            "name": "Query API",
            "command": "python -m cli.main system query-api",
            "description": "Interactive API endpoint execution with parameter resolution",
            "category": "system"
        }
    ],
    "Examples": [
        {
            "name": "Hello Example",
            "command": "python -m cli.main example hello",
            "description": "Simple greeting command (requires name parameter)",
            "category": "example",
            "params": ["name"]
        }
    ],
    "Utility Scripts": [
        {
            "name": "Generate Endpoints",
            "command": "python scripts/generate_endpoints.py",
            "description": "Generate endpoint functions from OpenAPI spec",
            "category": "utility"
        },
        {
            "name": "Watch OpenAPI",
            "command": "python scripts/watch_openapi.py",
            "description": "Watch for OpenAPI spec changes and auto-regenerate",
            "category": "utility"
        },
        {
            "name": "Regenerate Client",
            "command": "python scripts/regen_client.py",
            "description": "Regenerate the API client from OpenAPI spec",
            "category": "utility"
        }
    ],
    "Direct API Endpoints": [
        {
            "name": "List Available Endpoints",
            "command": "ls -la cli/endpoints/gettattle/",
            "description": "Show all generated API endpoint modules",
            "category": "info"
        }
    ]
}


def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def show_banner():
    """Display the application banner."""
    banner = Panel.fit(
        Text("API Central Interactive Terminal", style="bold cyan"),
        subtitle="Test and explore available functions",
        border_style="cyan"
    )
    console.print(banner)
    console.print()


def show_commands_table():
    """Display all available commands in a formatted table."""
    table = Table(title="Available Commands", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", width=6)
    table.add_column("Category", style="green", width=15)
    table.add_column("Name", style="yellow", width=25)
    table.add_column("Description", width=50)
    
    command_id = 1
    command_map = {}
    
    for category, commands in COMMANDS.items():
        for cmd in commands:
            table.add_row(
                str(command_id),
                category,
                cmd["name"],
                cmd["description"]
            )
            command_map[command_id] = (category, cmd)
            command_id += 1
    
    console.print(table)
    return command_map


def execute_command(command_info: Dict, category: str):
    """Execute a selected command."""
    console.print(f"\n[bold cyan]Executing:[/bold cyan] {command_info['name']}")
    console.print(f"[dim]Command:[/dim] {command_info['command']}")
    
    # Handle commands that need parameters
    full_command = command_info['command']
    
    if command_info.get('params'):
        console.print("\n[yellow]This command requires parameters:[/yellow]")
        params = []
        for param in command_info['params']:
            value = Prompt.ask(f"Enter value for '{param}'")
            params.append(value)
        full_command = f"{command_info['command']} {' '.join(params)}"
    
    console.print(f"\n[dim]Executing: {full_command}[/dim]\n")
    
    try:
        # Execute the command
        result = subprocess.run(
            full_command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        if result.stdout:
            console.print("[green]Output:[/green]")
            console.print(result.stdout)
        
        if result.stderr:
            console.print("[red]Errors:[/red]")
            console.print(result.stderr)
            
        if result.returncode != 0:
            console.print(f"[red]Command exited with code {result.returncode}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error executing command: {e}[/red]")


def show_endpoint_details():
    """Show detailed information about available API endpoints."""
    console.print("\n[bold cyan]Available API Endpoint Modules:[/bold cyan]\n")
    
    endpoints_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cli/endpoints/gettattle")
    
    if os.path.exists(endpoints_dir):
        files = [f for f in os.listdir(endpoints_dir) if f.endswith('.py') and f != '__init__.py']
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Module", style="cyan", width=35)
        table.add_column("Description", width=45)
        
        endpoint_descriptions = {
            "channels.py": "Channel management endpoints",
            "delivery-services.py": "Delivery service operations",
            "groups.py": "Group management functions",
            "incidents.py": "Incident tracking and management",
            "localization-codes.py": "Localization and language codes",
            "locations.py": "Location-based operations",
            "merchants.py": "Merchant account management",
            "orders.py": "Order processing endpoints",
            "rewards.py": "Reward system operations",
            "users.py": "User management functions",
            "surveys.py": "Survey creation and management",
            "webhooks.py": "Webhook subscription management"
        }
        
        for file in sorted(files):
            desc = endpoint_descriptions.get(file, "API endpoints")
            table.add_row(file, desc)
        
        console.print(table)
    else:
        console.print("[yellow]Endpoints directory not found. You may need to generate endpoints first.[/yellow]")


def main():
    """Main interactive loop."""
    clear_screen()
    show_banner()
    
    console.print("[bold]Welcome to the API Central Interactive Terminal![/bold]\n")
    console.print("This tool allows you to explore and test all available functions")
    console.print("in the api-central project.\n")
    
    while True:
        # Show main menu
        console.print("\n[bold cyan]Main Menu:[/bold cyan]")
        console.print("1. Show all commands")
        console.print("2. Show API endpoint details")
        console.print("3. Execute a command")
        console.print("4. Clear screen")
        console.print("5. Exit")
        
        choice = Prompt.ask("\nSelect an option", choices=["1", "2", "3", "4", "5"], default="1")
        
        if choice == "1":
            console.print()
            command_map = show_commands_table()
            
        elif choice == "2":
            show_endpoint_details()
            
        elif choice == "3":
            command_map = show_commands_table()
            console.print()
            
            command_id = Prompt.ask("Enter command ID to execute (or 'back' to return)")
            
            if command_id.lower() == 'back':
                continue
                
            try:
                cmd_id = int(command_id)
                if cmd_id in command_map:
                    category, cmd_info = command_map[cmd_id]
                    
                    # Confirm execution
                    if Confirm.ask(f"\nExecute '{cmd_info['name']}'?"):
                        execute_command(cmd_info, category)
                        
                        # Ask if user wants to continue
                        if not Confirm.ask("\nWould you like to execute another command?"):
                            break
                else:
                    console.print("[red]Invalid command ID[/red]")
                    
            except ValueError:
                console.print("[red]Please enter a valid number[/red]")
                
        elif choice == "4":
            clear_screen()
            show_banner()
            
        elif choice == "5":
            console.print("\n[bold green]Thank you for using API Central Interactive Terminal![/bold green]")
            break
    
    console.print("\n[dim]Goodbye![/dim]\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user. Exiting...[/yellow]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]An error occurred: {e}[/red]\n")
        sys.exit(1)