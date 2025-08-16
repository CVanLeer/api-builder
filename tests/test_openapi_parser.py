"""Tests for OpenAPI parser implementation."""

import json
import pytest
from pathlib import Path

from parsers.openapi import OpenAPIParser
from parsers import APISpecification, AuthConfig


@pytest.fixture
def sample_openapi_spec():
    """Load sample OpenAPI specification."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    with open(fixtures_dir / "openapi_spec.json") as f:
        return json.load(f)


@pytest.fixture
def openapi_parser():
    """Create OpenAPIParser instance."""
    return OpenAPIParser()


def test_parse_valid_spec(openapi_parser, sample_openapi_spec):
    """Test parsing a valid OpenAPI specification."""
    spec = openapi_parser.parse(sample_openapi_spec)
    
    assert isinstance(spec, APISpecification)
    assert spec.metadata.title == "Sample API"
    assert spec.metadata.version == "1.0.0"
    assert spec.metadata.description == "A sample OpenAPI specification for testing"


def test_parse_spec_metadata(openapi_parser, sample_openapi_spec):
    """Test parsing OpenAPI metadata."""
    spec = openapi_parser.parse(sample_openapi_spec)
    
    assert spec.metadata.contact["name"] == "API Support"
    assert spec.metadata.contact["email"] == "support@example.com"
    assert spec.metadata.license["name"] == "MIT"
    assert spec.metadata.base_url == "https://api.example.com/v1"


def test_parse_spec_authentication(openapi_parser, sample_openapi_spec):
    """Test parsing authentication configuration."""
    spec = openapi_parser.parse(sample_openapi_spec)
    
    assert spec.auth_config.type == "bearer"
    assert spec.auth_config.location == "header"


def test_parse_spec_schemas(openapi_parser, sample_openapi_spec):
    """Test parsing schema definitions."""
    spec = openapi_parser.parse(sample_openapi_spec)
    
    assert "User" in spec.schemas
    assert "Error" in spec.schemas
    
    user_schema = spec.schemas["User"]
    assert user_schema["type"] == "object"
    assert "id" in user_schema["properties"]
    assert "name" in user_schema["properties"]
    assert "email" in user_schema["properties"]


def test_parse_spec_endpoints(openapi_parser, sample_openapi_spec):
    """Test parsing endpoints from OpenAPI spec."""
    spec = openapi_parser.parse(sample_openapi_spec)
    
    # Should have 3 endpoints (GET /users, POST /users, GET /health)
    assert len(spec.endpoints) == 3
    
    # Check endpoint paths and methods
    endpoint_info = [(ep.method, ep.path) for ep in spec.endpoints]
    assert ("GET", "/users") in endpoint_info
    assert ("POST", "/users") in endpoint_info
    assert ("GET", "/health") in endpoint_info


def test_parse_endpoint_with_parameters(openapi_parser, sample_openapi_spec):
    """Test parsing endpoint with query parameters."""
    spec = openapi_parser.parse(sample_openapi_spec)
    
    # Find the GET /users endpoint
    get_users = None
    for ep in spec.endpoints:
        if ep.method == "GET" and ep.path == "/users":
            get_users = ep
            break
    
    assert get_users is not None
    assert len(get_users.parameters) == 2
    
    # Check parameters
    param_names = [p.name for p in get_users.parameters]
    assert "limit" in param_names
    assert "offset" in param_names
    
    # Check parameter properties
    limit_param = next(p for p in get_users.parameters if p.name == "limit")
    assert limit_param.location == "query"
    assert limit_param.type_info == "integer"


def test_parse_endpoint_with_request_body(openapi_parser, sample_openapi_spec):
    """Test parsing endpoint with request body."""
    spec = openapi_parser.parse(sample_openapi_spec)
    
    # Find the POST /users endpoint
    post_users = None
    for ep in spec.endpoints:
        if ep.method == "POST" and ep.path == "/users":
            post_users = ep
            break
    
    assert post_users is not None
    assert post_users.request_body is not None
    assert post_users.request_body["type"] == "raw"
    assert post_users.request_body["mimeType"] == "application/json"


def test_parse_endpoint_responses(openapi_parser, sample_openapi_spec):
    """Test parsing endpoint responses."""
    spec = openapi_parser.parse(sample_openapi_spec)
    
    # Find the GET /users endpoint
    get_users = None
    for ep in spec.endpoints:
        if ep.method == "GET" and ep.path == "/users":
            get_users = ep
            break
    
    assert get_users is not None
    assert len(get_users.responses) == 2
    
    # Check status codes
    status_codes = [r.status_code for r in get_users.responses]
    assert 200 in status_codes
    assert 400 in status_codes
    
    # Check response descriptions
    success_response = next(r for r in get_users.responses if r.status_code == 200)
    assert success_response.description == "Successful response"


def test_parse_endpoint_tags(openapi_parser, sample_openapi_spec):
    """Test parsing endpoint tags."""
    spec = openapi_parser.parse(sample_openapi_spec)
    
    # Find users endpoints
    users_endpoints = [ep for ep in spec.endpoints if ep.path == "/users"]
    
    for ep in users_endpoints:
        assert "Users" in ep.tags
    
    # Health endpoint should have no tags
    health_endpoints = [ep for ep in spec.endpoints if ep.path == "/health"]
    assert len(health_endpoints) == 1
    assert health_endpoints[0].tags == []


def test_validate_valid_spec(openapi_parser, sample_openapi_spec):
    """Test validation of a valid specification."""
    spec = openapi_parser.parse(sample_openapi_spec)
    errors = openapi_parser.validate(spec)
    
    assert len(errors) == 0


def test_parse_invalid_json(openapi_parser):
    """Test parsing invalid JSON."""
    with pytest.raises(ValueError, match="Invalid JSON"):
        openapi_parser.parse("invalid json")


def test_parse_non_openapi_spec(openapi_parser):
    """Test parsing non-OpenAPI data."""
    invalid_data = {"not": "an openapi spec"}
    
    with pytest.raises(ValueError, match="Not a valid OpenAPI"):
        openapi_parser.parse(invalid_data)


def test_parse_swagger_2_spec(openapi_parser):
    """Test parsing Swagger 2.0 specification."""
    swagger_spec = {
        "swagger": "2.0",
        "info": {
            "title": "Swagger API",
            "version": "1.0.0"
        },
        "host": "api.example.com",
        "basePath": "/v1",
        "schemes": ["https"],
        "paths": {
            "/test": {
                "get": {
                    "summary": "Test endpoint",
                    "responses": {
                        "200": {
                            "description": "Success"
                        }
                    }
                }
            }
        }
    }
    
    spec = openapi_parser.parse(swagger_spec)
    assert spec.metadata.title == "Swagger API"
    assert spec.metadata.base_url == "https://api.example.com/v1"
    assert len(spec.endpoints) == 1


def test_parse_spec_without_servers(openapi_parser):
    """Test parsing OpenAPI spec without servers."""
    minimal_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Minimal API",
            "version": "1.0.0"
        },
        "paths": {}
    }
    
    spec = openapi_parser.parse(minimal_spec)
    assert spec.metadata.title == "Minimal API"
    assert spec.metadata.base_url == ""


def test_parse_string_input(openapi_parser, sample_openapi_spec):
    """Test parsing from JSON string."""
    json_string = json.dumps(sample_openapi_spec)
    spec = openapi_parser.parse(json_string)
    
    assert isinstance(spec, APISpecification)
    assert spec.metadata.title == "Sample API"


def test_parse_different_security_schemes(openapi_parser):
    """Test parsing different security schemes."""
    # Test API key security
    apikey_spec = {
        "openapi": "3.0.0",
        "info": {"title": "API Key API", "version": "1.0.0"},
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key"
                }
            }
        },
        "paths": {}
    }
    
    spec = openapi_parser.parse(apikey_spec)
    assert spec.auth_config.type == "apikey"
    assert spec.auth_config.location == "header"
    assert spec.auth_config.name == "X-API-Key"