#!/usr/bin/env python3
"""
Example: Proper Error Handling with API Builder

This script demonstrates how to:
1. Handle different types of API errors gracefully
2. Implement retry logic for transient failures
3. Provide meaningful error messages to users
4. Recover from authentication issues
5. Log errors for debugging

Requirements:
    - Python 3.12+
    - API Builder installed and authenticated
"""

import json
import sys
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.utils.api_client import get_client, authenticate_client
from cli.config import get_saved_token, auto_authenticate, get_saved_credentials
from cli.state import state_manager
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import requests

console = Console()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_errors.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class APIError:
    """Structured representation of API errors."""
    error_type: str
    message: str
    status_code: Optional[int] = None
    endpoint: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    is_retryable: bool = False


class ErrorHandler:
    """Centralized error handling for API operations."""
    
    def __init__(self):
        self.console = console
        
    def classify_error(self, exception: Exception, endpoint: str = None) -> APIError:
        """
        Classify an exception into a structured APIError.
        
        Args:
            exception: The exception that occurred
            endpoint: The endpoint that was called when the error occurred
            
        Returns:
            APIError: Structured error information
        """
        if isinstance(exception, requests.exceptions.ConnectionError):
            return APIError(
                error_type="CONNECTION_ERROR",
                message="Unable to connect to the API. Check your internet connection and API URL.",
                endpoint=endpoint,
                is_retryable=True
            )
        
        elif isinstance(exception, requests.exceptions.Timeout):
            return APIError(
                error_type="TIMEOUT",
                message="API request timed out. The server may be overloaded.",
                endpoint=endpoint,
                is_retryable=True
            )
        
        elif isinstance(exception, requests.exceptions.HTTPError):
            status_code = getattr(exception.response, 'status_code', None)
            
            if status_code == 401:
                return APIError(
                    error_type="AUTHENTICATION_ERROR",
                    message="Authentication failed. Token may be expired or invalid.",
                    status_code=status_code,
                    endpoint=endpoint,
                    is_retryable=True  # Can retry after re-authentication
                )
            elif status_code == 403:
                return APIError(
                    error_type="AUTHORIZATION_ERROR", 
                    message="Access forbidden. Check your API permissions.",
                    status_code=status_code,
                    endpoint=endpoint,
                    is_retryable=False
                )
            elif status_code == 404:
                return APIError(
                    error_type="NOT_FOUND",
                    message=f"Endpoint not found: {endpoint}",
                    status_code=status_code,
                    endpoint=endpoint,
                    is_retryable=False
                )
            elif status_code == 429:
                return APIError(
                    error_type="RATE_LIMIT",
                    message="Rate limit exceeded. Please wait before making more requests.",
                    status_code=status_code,
                    endpoint=endpoint,
                    is_retryable=True
                )
            elif 500 <= status_code < 600:
                return APIError(
                    error_type="SERVER_ERROR",
                    message="Server error. The API service may be temporarily unavailable.",
                    status_code=status_code,
                    endpoint=endpoint,
                    is_retryable=True
                )
            else:
                return APIError(
                    error_type="HTTP_ERROR",
                    message=f"HTTP {status_code} error occurred",
                    status_code=status_code,
                    endpoint=endpoint,
                    is_retryable=False
                )
        
        elif isinstance(exception, json.JSONDecodeError):
            return APIError(
                error_type="INVALID_RESPONSE",
                message="API returned invalid JSON response",
                endpoint=endpoint,
                details={"json_error": str(exception)},
                is_retryable=False
            )
        
        else:
            return APIError(
                error_type="UNKNOWN_ERROR",
                message=f"Unexpected error: {str(exception)}",
                endpoint=endpoint,
                details={"exception_type": type(exception).__name__},
                is_retryable=False
            )
    
    def display_error(self, error: APIError):
        """Display a formatted error message to the user."""
        icon = "🔄" if error.is_retryable else "❌"
        
        self.console.print(f"\n[red]{icon} {error.error_type}[/red]")
        self.console.print(f"[yellow]{error.message}[/yellow]")
        
        if error.endpoint:
            self.console.print(f"[dim]Endpoint: {error.endpoint}[/dim]")
        
        if error.status_code:
            self.console.print(f"[dim]Status Code: {error.status_code}[/dim]")
        
        if error.details:
            self.console.print(f"[dim]Details: {error.details}[/dim]")
    
    def log_error(self, error: APIError, context: Dict[str, Any] = None):
        """Log error information for debugging."""
        log_data = {
            "error_type": error.error_type,
            "message": error.message,
            "endpoint": error.endpoint,
            "status_code": error.status_code,
            "is_retryable": error.is_retryable,
            "details": error.details,
            "context": context or {}
        }
        
        logger.error(f"API Error: {json.dumps(log_data, indent=2)}")


class ResilientAPIClient:
    """API client wrapper with built-in error handling and retry logic."""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.error_handler = ErrorHandler()
        
    def _should_retry(self, error: APIError, attempt: int) -> bool:
        """Determine if an operation should be retried."""
        if attempt >= self.max_retries:
            return False
            
        if not error.is_retryable:
            return False
            
        # Special handling for rate limits
        if error.error_type == "RATE_LIMIT":
            # Wait longer for rate limit errors
            time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
            return True
            
        return True
    
    def _handle_auth_error(self) -> bool:
        """Attempt to recover from authentication errors."""
        console.print("[yellow]🔄 Attempting to refresh authentication...[/yellow]")
        
        # Try automatic authentication first
        if auto_authenticate():
            console.print("[green]✅ Authentication refreshed automatically[/green]")
            return True
        
        # If auto-auth fails, prompt for manual authentication
        console.print("[yellow]Automatic authentication failed. Manual authentication required.[/yellow]")
        
        email, _ = get_saved_credentials()
        if not email:
            email = input("Email: ")
        
        password = input("Password: ")
        
        try:
            token = authenticate_client(email, password)
            if token:
                state_manager.save_token(token)
                console.print("[green]✅ Authentication successful[/green]")
                return True
            else:
                console.print("[red]❌ Authentication failed[/red]")
                return False
        except Exception as e:
            console.print(f"[red]❌ Authentication error: {e}[/red]")
            return False
    
    def call_endpoint(
        self, 
        endpoint_name: str,
        client_method,
        **kwargs
    ) -> Optional[Union[Dict[str, Any], list]]:
        """
        Make an API call with automatic error handling and retry logic.
        
        Args:
            endpoint_name: Human-readable name of the endpoint
            client_method: The API client method to call
            **kwargs: Parameters to pass to the method
            
        Returns:
            The API response data, or None if all attempts failed
        """
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    console.print(f"[yellow]🔄 Retry attempt {attempt}/{self.max_retries}[/yellow]")
                    time.sleep(self.retry_delay * attempt)  # Linear backoff
                
                response = client_method(**kwargs)
                
                if response is not None:
                    console.print(f"[green]✅ Successfully called {endpoint_name}[/green]")
                    return response
                else:
                    console.print(f"[yellow]⚠️ {endpoint_name} returned no data[/yellow]")
                    return None
                    
            except Exception as e:
                error = self.error_handler.classify_error(e, endpoint_name)
                
                # Log the error
                self.error_handler.log_error(error, {
                    "attempt": attempt + 1,
                    "max_retries": self.max_retries,
                    "kwargs": kwargs
                })
                
                # Handle authentication errors specially
                if error.error_type == "AUTHENTICATION_ERROR":
                    if self._handle_auth_error():
                        continue  # Retry with new authentication
                    else:
                        self.error_handler.display_error(error)
                        return None
                
                # Check if we should retry
                if self._should_retry(error, attempt):
                    self.error_handler.display_error(error)
                    console.print(f"[cyan]⏳ Waiting {self.retry_delay * (attempt + 1)} seconds before retry...[/cyan]")
                    continue
                else:
                    # Final failure
                    self.error_handler.display_error(error)
                    if attempt == self.max_retries:
                        console.print(f"[red]❌ Failed after {self.max_retries + 1} attempts[/red]")
                    return None
        
        return None


def demonstrate_error_handling():
    """Demonstrate various error handling scenarios."""
    console.print("[bold]Error Handling Example[/bold]\n")
    
    # Initialize resilient client
    api_client = ResilientAPIClient(max_retries=3, retry_delay=1.0)
    
    try:
        # Get the base API client
        client = get_client()
        
        # Test 1: Valid API call
        console.print("[cyan]Test 1: Valid API call[/cyan]")
        merchants = api_client.call_endpoint(
            "merchants",
            client.merchants.get_merchants.sync
        )
        
        if merchants:
            data = merchants.get('data', merchants) if isinstance(merchants, dict) else merchants
            if isinstance(data, list):
                console.print(f"[green]✅ Retrieved {len(data)} merchants[/green]")
            else:
                console.print("[green]✅ Retrieved merchant data[/green]")
        
        # Test 2: Endpoint that might not exist
        console.print("\n[cyan]Test 2: Potentially invalid endpoint[/cyan]")
        try:
            # This might fail if the endpoint doesn't exist
            invalid_data = api_client.call_endpoint(
                "non-existent-endpoint",
                getattr(client, 'non_existent', lambda: None)
            )
        except AttributeError:
            console.print("[yellow]⚠️ Endpoint not available in API client[/yellow]")
        
        # Test 3: Demonstrate parameter validation
        console.print("\n[cyan]Test 3: Parameter validation[/cyan]")
        try:
            # Try calling with invalid parameters
            result = api_client.call_endpoint(
                "merchants with invalid params",
                client.merchants.get_merchants.sync,
                invalid_param="this_should_fail"
            )
        except Exception:
            console.print("[yellow]⚠️ Parameter validation caught invalid parameters[/yellow]")
        
        # Test 4: Show error log location
        console.print(f"\n[dim]📋 Error logs are saved to: api_errors.log[/dim]")
        console.print(f"[dim]💡 Check the log file for detailed error information[/dim]")
        
    except Exception as e:
        error_handler = ErrorHandler()
        error = error_handler.classify_error(e)
        error_handler.display_error(error)
        error_handler.log_error(error)


def demonstrate_recovery_strategies():
    """Show different recovery strategies for common error scenarios."""
    console.print("\n[bold]Recovery Strategies[/bold]\n")
    
    strategies = [
        {
            "scenario": "Authentication Token Expired",
            "strategy": "Automatically refresh token using saved credentials",
            "implementation": "auto_authenticate() function"
        },
        {
            "scenario": "Rate Limit Exceeded", 
            "strategy": "Exponential backoff with increasing delays",
            "implementation": "Built into ResilientAPIClient"
        },
        {
            "scenario": "Network Timeout",
            "strategy": "Retry with linear backoff up to 3 times",
            "implementation": "Configurable retry logic"
        },
        {
            "scenario": "Server Error (5xx)",
            "strategy": "Retry after delay, log for monitoring",
            "implementation": "Error classification + retry"
        },
        {
            "scenario": "Invalid JSON Response",
            "strategy": "Log error and fail gracefully",
            "implementation": "JSONDecodeError handling"
        }
    ]
    
    table = Table(title="Error Recovery Strategies")
    table.add_column("Scenario", style="red")
    table.add_column("Strategy", style="yellow")
    table.add_column("Implementation", style="green")
    
    for strategy in strategies:
        table.add_row(
            strategy["scenario"],
            strategy["strategy"],
            strategy["implementation"]
        )
    
    console.print(table)


def main():
    """Main function demonstrating error handling patterns."""
    try:
        demonstrate_error_handling()
        demonstrate_recovery_strategies()
        
        console.print("\n[bold green]✅ Error handling examples completed![/bold green]")
        console.print("[dim]Check api_errors.log for detailed error logs[/dim]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo cancelled by user[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[red]❌ Unexpected error in demo: {e}[/red]")
        logger.exception("Unexpected error in error handling demo")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)