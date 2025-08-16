"""Tests for Insomnia parser implementation."""

import json
import pytest
from pathlib import Path

from parsers.insomnia import InsomniaParser
from parsers import APISpecification, AuthConfig


@pytest.fixture
def sample_insomnia_export():
    """Load sample Insomnia export."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    with open(fixtures_dir / "insomnia_export.json") as f:
        return json.load(f)


@pytest.fixture
def insomnia_parser():
    """Create InsomniaParser instance."""
    return InsomniaParser()


def test_parse_valid_export(insomnia_parser, sample_insomnia_export):
    """Test parsing a valid Insomnia export."""
    spec = insomnia_parser.parse(sample_insomnia_export)
    
    assert isinstance(spec, APISpecification)
    assert spec.metadata.title == "Sample API Workspace"
    assert spec.metadata.description == "A sample Insomnia workspace for testing"


def test_parse_export_environment_variables(insomnia_parser, sample_insomnia_export):
    """Test parsing environment variables."""
    spec = insomnia_parser.parse(sample_insomnia_export)
    
    assert "base_url" in spec.variables
    assert spec.variables["base_url"] == "https://api.example.com"
    assert "api_key" in spec.variables
    assert spec.variables["api_key"] == "secret-key"


def test_parse_export_authentication(insomnia_parser, sample_insomnia_export):
    """Test parsing authentication from requests."""
    spec = insomnia_parser.parse(sample_insomnia_export)
    
    # Should detect bearer auth from requests
    assert spec.auth_config.type == "bearer"
    assert spec.auth_config.location == "header"


def test_parse_export_endpoints(insomnia_parser, sample_insomnia_export):
    """Test parsing endpoints from export."""
    spec = insomnia_parser.parse(sample_insomnia_export)
    
    # Should have 3 requests
    assert len(spec.endpoints) == 3
    
    # Check endpoint names
    endpoint_names = [ep.name for ep in spec.endpoints]
    assert "Get Users" in endpoint_names
    assert "Create User" in endpoint_names
    assert "Health Check" in endpoint_names


def test_parse_request_with_parameters(insomnia_parser, sample_insomnia_export):
    """Test parsing request with query parameters."""
    spec = insomnia_parser.parse(sample_insomnia_export)
    
    # Find the Get Users endpoint
    get_users = None
    for ep in spec.endpoints:
        if ep.name == "Get Users":
            get_users = ep
            break
    
    assert get_users is not None
    
    # Check parameters (query + headers)
    query_params = [p for p in get_users.parameters if p.location == "query"]
    assert len(query_params) == 2
    
    param_names = [p.name for p in query_params]
    assert "limit" in param_names
    assert "offset" in param_names
    
    # Check headers
    header_params = [p for p in get_users.parameters if p.location == "header"]
    assert len(header_params) == 1
    assert header_params[0].name == "Accept"


def test_parse_request_with_body(insomnia_parser, sample_insomnia_export):
    """Test parsing request with body."""
    spec = insomnia_parser.parse(sample_insomnia_export)
    
    # Find the Create User endpoint
    create_user = None
    for ep in spec.endpoints:
        if ep.name == "Create User":
            create_user = ep
            break
    
    assert create_user is not None
    assert create_user.request_body is not None
    assert create_user.request_body["type"] == "raw"
    assert "Jane Doe" in create_user.request_body["content"]
    assert create_user.request_body["mimeType"] == "application/json"


def test_parse_request_groups_as_tags(insomnia_parser, sample_insomnia_export):
    """Test parsing request groups as endpoint tags."""
    spec = insomnia_parser.parse(sample_insomnia_export)
    
    # Find endpoints in Users group
    users_endpoints = [ep for ep in spec.endpoints if "Users" in ep.tags]
    assert len(users_endpoints) == 2
    
    # Health check should not have group tag (direct child of workspace)
    health_endpoints = [ep for ep in spec.endpoints if ep.name == "Health Check"]
    assert len(health_endpoints) == 1
    assert health_endpoints[0].tags == []


def test_validate_valid_spec(insomnia_parser, sample_insomnia_export):
    """Test validation of a valid specification."""
    spec = insomnia_parser.parse(sample_insomnia_export)
    errors = insomnia_parser.validate(spec)
    
    assert len(errors) == 0


def test_parse_invalid_json(insomnia_parser):
    """Test parsing invalid JSON."""
    with pytest.raises(ValueError, match="Invalid JSON"):
        insomnia_parser.parse("invalid json")


def test_parse_non_insomnia_export(insomnia_parser):
    """Test parsing non-Insomnia data."""
    invalid_data = {"not": "an insomnia export"}
    
    with pytest.raises(ValueError, match="Not a valid Insomnia export"):
        insomnia_parser.parse(invalid_data)


def test_parse_empty_export(insomnia_parser):
    """Test parsing export with no requests."""
    empty_export = {
        "_type": "export",
        "__export_format": 4,
        "resources": [
            {
                "_id": "wrk_1",
                "_type": "workspace",
                "name": "Empty Workspace"
            }
        ]
    }
    
    spec = insomnia_parser.parse(empty_export)
    errors = insomnia_parser.validate(spec)
    
    assert len(errors) == 1
    assert "No requests found" in errors[0]


def test_parse_no_workspace_name(insomnia_parser):
    """Test parsing export without workspace name."""
    export_no_workspace = {
        "_type": "export",
        "__export_format": 4,
        "resources": [
            {
                "_id": "req_1",
                "_type": "request",
                "name": "Test Request",
                "method": "GET",
                "url": "https://example.com"
            }
        ]
    }
    
    spec = insomnia_parser.parse(export_no_workspace)
    assert spec.metadata.title == "Insomnia Workspace"


def test_parse_string_input(insomnia_parser, sample_insomnia_export):
    """Test parsing from JSON string."""
    json_string = json.dumps(sample_insomnia_export)
    spec = insomnia_parser.parse(json_string)
    
    assert isinstance(spec, APISpecification)
    assert spec.metadata.title == "Sample API Workspace"


def test_parse_different_auth_types(insomnia_parser):
    """Test parsing different authentication types."""
    basic_auth_export = {
        "_type": "export",
        "__export_format": 4,
        "resources": [
            {
                "_id": "req_1",
                "_type": "request",
                "name": "Basic Auth Request",
                "method": "GET",
                "url": "https://example.com",
                "authentication": {
                    "type": "basic",
                    "username": "user",
                    "password": "pass"
                }
            }
        ]
    }
    
    spec = insomnia_parser.parse(basic_auth_export)
    assert spec.auth_config.type == "basic"
    assert spec.auth_config.location == "header"