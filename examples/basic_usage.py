#!/usr/bin/env python3
"""
Example: Basic API Integration

This script demonstrates how to:
1. Connect to an API using API Builder
2. Authenticate with stored credentials
3. Make basic API calls
4. Handle responses and errors

Requirements:
    - Python 3.12+
    - API Builder installed (poetry install)
    - Valid API credentials in .env or via auth command
"""

import json
import sys
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.utils.api_client import get_client
from cli.config import get_saved_token
from cli.state import state_manager
from rich.console import Console
from rich.table import Table

console = Console()


def check_authentication() -> bool:
    """
    Check if we have a valid authentication token.
    
    Returns:
        bool: True if authenticated, False otherwise
    """
    token = get_saved_token()
    if not token:
        console.print("[red]❌ No authentication token found![/red]")
        console.print("[yellow]Run: python cli/main.py auth get-token[/yellow]")
        return False
    
    console.print("[green]✅ Authentication token found[/green]")
    return True


def list_merchants():
    """
    Retrieve and display a list of merchants.
    
    This is typically a good starting point as merchant endpoints
    usually don't require complex parameters.
    """
    try:
        console.print("[cyan]Fetching merchants...[/cyan]")
        
        client = get_client()
        # Call the merchants endpoint
        response = client.merchants.get_merchants.sync()
        
        if response:
            # Extract data from response
            data = response.get('data', response) if isinstance(response, dict) else response
            
            if isinstance(data, list) and data:
                console.print(f"[green]✅ Found {len(data)} merchants[/green]")
                
                # Display in a nice table
                table = Table(title="Merchants")
                
                # Use the keys from the first item to create columns
                if isinstance(data[0], dict):
                    columns = list(data[0].keys())[:5]  # Show first 5 columns
                    for col in columns:
                        table.add_column(col, style="cyan")
                    
                    # Show first 10 merchants
                    for merchant in data[:10]:
                        row = [str(merchant.get(col, '')) for col in columns]
                        table.add_row(*row)
                    
                    console.print(table)
                    
                    if len(data) > 10:
                        console.print(f"[dim]... and {len(data) - 10} more merchants[/dim]")
                
                return data
            else:
                console.print("[yellow]⚠️ No merchant data found[/yellow]")
                return []
        else:
            console.print("[red]❌ Failed to fetch merchants[/red]")
            return []
            
    except Exception as e:
        console.print(f"[red]❌ Error fetching merchants: {e}[/red]")
        return []


def get_merchant_details(merchant_id: str):
    """
    Get detailed information for a specific merchant.
    
    Args:
        merchant_id: The ID of the merchant to fetch details for
    """
    try:
        console.print(f"[cyan]Fetching details for merchant {merchant_id}...[/cyan]")
        
        client = get_client()
        # This assumes your API has a merchant details endpoint
        # Adjust the method name based on your generated client
        response = client.merchants.get_merchant.sync(merchant_id=merchant_id)
        
        if response:
            console.print("[green]✅ Merchant details retrieved[/green]")
            console.print(json.dumps(response, indent=2))
            return response
        else:
            console.print(f"[red]❌ Failed to fetch details for merchant {merchant_id}[/red]")
            return None
            
    except AttributeError:
        console.print("[yellow]⚠️ Merchant details endpoint not available in API[/yellow]")
        return None
    except Exception as e:
        console.print(f"[red]❌ Error fetching merchant details: {e}[/red]")
        return None


def save_data_to_file(data, filename: str = "api_data.json"):
    """
    Save API response data to a JSON file.
    
    Args:
        data: The data to save
        filename: Name of the file to save to
    """
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        console.print(f"[green]✅ Data saved to {filename}[/green]")
    except Exception as e:
        console.print(f"[red]❌ Error saving data: {e}[/red]")


def main():
    """
    Main function demonstrating basic API usage.
    """
    console.print("[bold]API Builder - Basic Usage Example[/bold]\n")
    
    # Step 1: Check authentication
    if not check_authentication():
        return 1
    
    # Step 2: Make a simple API call
    merchants = list_merchants()
    
    if not merchants:
        console.print("[red]Unable to fetch merchants. Check your API configuration.[/red]")
        return 1
    
    # Step 3: Save the data
    save_data_to_file(merchants, "merchants.json")
    
    # Step 4: Try to get details for the first merchant
    if isinstance(merchants, list) and merchants:
        first_merchant = merchants[0]
        if isinstance(first_merchant, dict) and 'id' in first_merchant:
            merchant_details = get_merchant_details(str(first_merchant['id']))
            if merchant_details:
                save_data_to_file(merchant_details, "merchant_details.json")
    
    console.print("\n[bold green]✅ Basic usage example completed![/bold green]")
    console.print("[dim]Check merchants.json and merchant_details.json for the results[/dim]")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)