"""
Pytest configuration and shared fixtures for API Builder tests.
"""
import pytest
from pathlib import Path
from typing import Dict, Any, List
import json
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta


@pytest.fixture
def sample_openapi_spec() -> Dict[str, Any]:
    """Provide a comprehensive sample OpenAPI specification for testing."""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0"
        },
        "paths": {
            "/merchants": {
                "get": {
                    "summary": "List merchants",
                    "parameters": [
                        {
                            "name": "page",
                            "type": "integer",
                            "required": False,
                            "default": 1
                        },
                        {
                            "name": "pageSize",
                            "type": "integer",
                            "required": False,
                            "default": 50
                        }
                    ],
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/MerchantList"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/merchants/{merchantId}": {
                "get": {
                    "summary": "Get merchant by ID",
                    "parameters": [
                        {
                            "name": "merchantId",
                            "type": "string",
                            "required": True
                        }
                    ],
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Merchant"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/locations": {
                "get": {
                    "summary": "List locations",
                    "parameters": [
                        {
                            "name": "merchantId",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "page",
                            "type": "integer",
                            "required": False
                        }
                    ],
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "locationId": {"type": "string"},
                                            "name": {"type": "string"},
                                            "address": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/orders": {
                "get": {
                    "summary": "List orders",
                    "parameters": [
                        {
                            "name": "locationId",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "startDate",
                            "type": "string",
                            "format": "date",
                            "required": False
                        },
                        {
                            "name": "endDate",
                            "type": "string",
                            "format": "date",
                            "required": False
                        },
                        {
                            "name": "status",
                            "type": "string",
                            "enum": ["pending", "completed", "cancelled"],
                            "required": False
                        }
                    ],
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "$ref": "#/components/schemas/Order"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "MerchantList": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {
                                "$ref": "#/components/schemas/Merchant"
                            }
                        },
                        "hasNextPage": {"type": "boolean"}
                    }
                },
                "Merchant": {
                    "type": "object",
                    "properties": {
                        "merchantId": {"type": "string"},
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "locations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "locationId": {"type": "string"},
                                    "name": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "Order": {
                    "type": "object",
                    "properties": {
                        "orderId": {"type": "string"},
                        "locationId": {"type": "string"},
                        "total": {"type": "number"},
                        "status": {"type": "string"}
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_api_responses() -> Dict[str, Any]:
    """Provide mock API responses for different endpoints."""
    return {
        "/merchants": {
            "data": [
                {
                    "merchantId": "merch-123",
                    "name": "Test Merchant",
                    "email": "test@merchant.com",
                    "locations": [
                        {"locationId": "loc-456", "name": "Main Location"}
                    ]
                },
                {
                    "merchantId": "merch-789",
                    "name": "Another Merchant",
                    "email": "another@merchant.com",
                    "locations": []
                }
            ],
            "hasNextPage": False
        },
        "/locations": {
            "data": [
                {
                    "locationId": "loc-456",
                    "name": "Main Location",
                    "address": "123 Main St",
                    "merchantId": "merch-123"
                },
                {
                    "locationId": "loc-789",
                    "name": "Secondary Location",
                    "address": "456 Oak Ave",
                    "merchantId": "merch-123"
                }
            ]
        },
        "/orders": {
            "data": [
                {
                    "orderId": "order-001",
                    "locationId": "loc-456",
                    "total": 99.99,
                    "status": "completed"
                },
                {
                    "orderId": "order-002",
                    "locationId": "loc-456",
                    "total": 150.00,
                    "status": "pending"
                }
            ]
        },
        "/auth/token": {
            "access_token": "test-token-123456",
            "token_type": "Bearer",
            "expires_in": 3600
        }
    }


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary state directory for testing."""
    state_dir = tmp_path / ".config" / "api-central"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


@pytest.fixture
def mock_state_manager(temp_state_dir, monkeypatch):
    """Mock the state manager with a temporary directory."""
    from cli.state import StateManager
    
    manager = StateManager()
    monkeypatch.setattr(manager, 'state_dir', temp_state_dir)
    monkeypatch.setattr(manager, 'state_file', temp_state_dir / "state.json")
    monkeypatch.setattr(manager, 'history_file', temp_state_dir / "command_history.json")
    return manager


@pytest.fixture
def sample_parameter_schemas() -> Dict[str, Any]:
    """Provide sample parameter schemas for testing parameter detection."""
    return {
        "merchantId": {
            "name": "merchantId",
            "type": "string",
            "required": True,
            "description": "The merchant identifier"
        },
        "locationId": {
            "name": "locationId", 
            "type": "string",
            "required": True,
            "description": "The location identifier"
        },
        "page": {
            "name": "page",
            "type": "integer",
            "required": False,
            "default": 1,
            "minimum": 1
        },
        "pageSize": {
            "name": "pageSize",
            "type": "integer",
            "required": False,
            "default": 50,
            "minimum": 1,
            "maximum": 100
        },
        "startDate": {
            "name": "startDate",
            "type": "string",
            "format": "date",
            "required": False
        },
        "status": {
            "name": "status",
            "type": "string",
            "enum": ["pending", "completed", "cancelled"],
            "required": False
        },
        "search": {
            "name": "search",
            "type": "string",
            "required": False
        },
        "isActive": {
            "name": "isActive",
            "type": "boolean",
            "required": False
        },
        "customerId": {
            "name": "customerId",
            "type": "string",
            "pattern": "^[a-zA-Z0-9-]+$",
            "required": True
        }
    }


@pytest.fixture
def mock_typer_context():
    """Mock Typer context for CLI testing."""
    from typer import Context
    from unittest.mock import MagicMock
    
    ctx = MagicMock(spec=Context)
    ctx.obj = {}
    return ctx


@pytest.fixture
def mock_requests_response():
    """Create a mock requests Response object."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"success": True}
    mock_response.text = '{"success": true}'
    return mock_response


@pytest.fixture
def mock_api_client():
    """Create a mock API client."""
    client = MagicMock()
    
    # Mock merchants endpoint
    client.merchants.get_merchants.sync.return_value = {
        "data": [
            {"merchantId": "merch-123", "name": "Test Merchant"}
        ]
    }
    
    # Mock locations endpoint
    client.locations.get_locations.sync.return_value = {
        "data": [
            {"locationId": "loc-456", "name": "Test Location"}
        ]
    }
    
    # Mock authentication
    client.authenticate.return_value = "test-token-123"
    
    return client


@pytest.fixture
def cli_runner():
    """Create a CLI test runner."""
    from typer.testing import CliRunner
    return CliRunner()


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # Reset any global state or singletons
    import cli.state
    if hasattr(cli.state, 'state_manager'):
        cli.state.state_manager = None
    
    # Clear any caches
    import cli.commands.system
    if hasattr(cli.commands.system, '_dependency_cache'):
        cli.commands.system._dependency_cache.clear()
    
    yield
    
    # Cleanup after test


@pytest.fixture
def mock_encryption_key():
    """Provide a mock encryption key for testing."""
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode()


@pytest.fixture
def sample_command_history() -> List[Dict[str, Any]]:
    """Provide sample command history for testing."""
    now = datetime.utcnow()
    return [
        {
            "timestamp": (now - timedelta(hours=2)).isoformat(),
            "endpoint": "/merchants",
            "parameters": {"page": 1, "pageSize": 50},
            "success": True
        },
        {
            "timestamp": (now - timedelta(hours=1)).isoformat(),
            "endpoint": "/locations",
            "parameters": {"merchantId": "merch-123"},
            "success": True
        },
        {
            "timestamp": now.isoformat(),
            "endpoint": "/orders",
            "parameters": {"locationId": "loc-456", "status": "completed"},
            "success": False
        }
    ]


@pytest.fixture
def mock_rich_console():
    """Mock Rich console for testing output."""
    from rich.console import Console
    from io import StringIO
    
    console = Console(file=StringIO(), force_terminal=True)
    return console


@pytest.fixture
def mock_prompts():
    """Mock user prompts for interactive testing."""
    return {
        "email": "test@example.com",
        "password": "test-password-123",
        "merchantId": "merch-123",
        "locationId": "loc-456",
        "confirm": "y"
    }