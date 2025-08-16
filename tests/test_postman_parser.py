"""Tests for Postman parser implementation."""

import json
import pytest
from pathlib import Path

from parsers.postman import PostmanParser
from parsers import APISpecification, AuthConfig


@pytest.fixture
def sample_postman_collection():
    """Load sample Postman collection."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    with open(fixtures_dir / "postman_collection.json") as f:
        return json.load(f)


@pytest.fixture
def postman_parser():
    """Create PostmanParser instance."""
    return PostmanParser()


def test_parse_valid_collection(postman_parser, sample_postman_collection):
    """Test parsing a valid Postman collection."""
    spec = postman_parser.parse(sample_postman_collection)
    
    assert isinstance(spec, APISpecification)
    assert spec.metadata.title == "Sample API Collection"
    assert spec.metadata.version == "1.0.0"
    assert spec.metadata.description == "A sample Postman collection for testing"


def test_parse_collection_authentication(postman_parser, sample_postman_collection):
    """Test parsing collection authentication."""
    spec = postman_parser.parse(sample_postman_collection)
    
    assert spec.auth_config.type == "bearer"
    assert spec.auth_config.location == "header"


def test_parse_collection_variables(postman_parser, sample_postman_collection):
    """Test parsing collection variables."""
    spec = postman_parser.parse(sample_postman_collection)
    
    assert "base_url" in spec.variables
    assert spec.variables["base_url"] == "https://api.example.com"
    assert "version" in spec.variables
    assert spec.variables["version"] == "v1"


def test_parse_collection_endpoints(postman_parser, sample_postman_collection):
    """Test parsing collection endpoints."""
    spec = postman_parser.parse(sample_postman_collection)
    
    # Should have 3 endpoints total
    assert len(spec.endpoints) == 3
    
    # Check endpoint names and methods
    endpoint_names = [ep.name for ep in spec.endpoints]
    assert "Get Users" in endpoint_names
    assert "Create User" in endpoint_names
    assert "Get Health Check" in endpoint_names
    
    # Check methods
    methods = [ep.method for ep in spec.endpoints]
    assert "GET" in methods
    assert "POST" in methods


def test_parse_endpoint_with_query_params(postman_parser, sample_postman_collection):
    """Test parsing endpoint with query parameters."""
    spec = postman_parser.parse(sample_postman_collection)
    
    # Find the Get Users endpoint
    get_users = None
    for ep in spec.endpoints:
        if ep.name == "Get Users":
            get_users = ep
            break
    
    assert get_users is not None
    assert len(get_users.parameters) >= 3  # limit, offset, Accept header
    
    # Check query parameters
    query_params = [p for p in get_users.parameters if p.location == "query"]
    assert len(query_params) == 2
    
    param_names = [p.name for p in query_params]
    assert "limit" in param_names
    assert "offset" in param_names


def test_parse_endpoint_with_request_body(postman_parser, sample_postman_collection):
    """Test parsing endpoint with request body."""
    spec = postman_parser.parse(sample_postman_collection)
    
    # Find the Create User endpoint
    create_user = None
    for ep in spec.endpoints:
        if ep.name == "Create User":
            create_user = ep
            break
    
    assert create_user is not None
    assert create_user.request_body is not None
    assert create_user.request_body["type"] == "raw"
    assert "John Doe" in create_user.request_body["content"]


def test_parse_folder_structure(postman_parser, sample_postman_collection):
    """Test parsing folder structure as tags."""
    spec = postman_parser.parse(sample_postman_collection)
    
    # Find endpoints in Users folder
    users_endpoints = [ep for ep in spec.endpoints if "Users" in ep.tags]
    assert len(users_endpoints) == 2
    
    # Health check should not have folder tag
    health_endpoints = [ep for ep in spec.endpoints if ep.name == "Get Health Check"]
    assert len(health_endpoints) == 1
    assert health_endpoints[0].tags == []


def test_validate_valid_spec(postman_parser, sample_postman_collection):
    """Test validation of a valid specification."""
    spec = postman_parser.parse(sample_postman_collection)
    errors = postman_parser.validate(spec)
    
    assert len(errors) == 0


def test_parse_invalid_json(postman_parser):
    """Test parsing invalid JSON."""
    with pytest.raises(ValueError, match="Invalid JSON"):
        postman_parser.parse("invalid json")


def test_parse_non_postman_collection(postman_parser):
    """Test parsing non-Postman data."""
    invalid_data = {"not": "a postman collection"}
    
    with pytest.raises(ValueError, match="Not a valid Postman collection"):
        postman_parser.parse(invalid_data)


def test_parse_empty_collection(postman_parser):
    """Test parsing empty collection."""
    empty_collection = {
        "info": {
            "name": "Empty Collection",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item": []
    }
    
    spec = postman_parser.parse(empty_collection)
    errors = postman_parser.validate(spec)
    
    assert len(errors) == 1
    assert "No endpoints found" in errors[0]


def test_parse_different_auth_types(postman_parser):
    """Test parsing different authentication types."""
    # Test API key auth
    apikey_collection = {
        "info": {
            "name": "API Key Collection",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "auth": {
            "type": "apikey",
            "apikey": [
                {"key": "in", "value": "header"},
                {"key": "key", "value": "X-Custom-Key"}
            ]
        },
        "item": []
    }
    
    spec = postman_parser.parse(apikey_collection)
    assert spec.auth_config.type == "apikey"
    assert spec.auth_config.location == "header"
    assert spec.auth_config.name == "X-Custom-Key"


def test_parse_string_input(postman_parser, sample_postman_collection):
    """Test parsing from JSON string."""
    json_string = json.dumps(sample_postman_collection)
    spec = postman_parser.parse(json_string)
    
    assert isinstance(spec, APISpecification)
    assert spec.metadata.title == "Sample API Collection"