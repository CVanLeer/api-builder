"""Tests for parser factory implementation."""

import json
import pytest
from pathlib import Path

from parsers.factory import ParserFactory
from parsers.postman import PostmanParser
from parsers.insomnia import InsomniaParser
from parsers.openapi import OpenAPIParser


@pytest.fixture
def fixtures_dir():
    """Get fixtures directory path."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_postman_collection(fixtures_dir):
    """Load sample Postman collection."""
    with open(fixtures_dir / "postman_collection.json") as f:
        return json.load(f)


@pytest.fixture
def sample_insomnia_export(fixtures_dir):
    """Load sample Insomnia export."""
    with open(fixtures_dir / "insomnia_export.json") as f:
        return json.load(f)


@pytest.fixture
def sample_openapi_spec(fixtures_dir):
    """Load sample OpenAPI specification."""
    with open(fixtures_dir / "openapi_spec.json") as f:
        return json.load(f)


def test_detect_postman_collection(sample_postman_collection):
    """Test detection of Postman collection format."""
    format_name = ParserFactory.detect_format(sample_postman_collection)
    assert format_name == "postman"


def test_detect_insomnia_export(sample_insomnia_export):
    """Test detection of Insomnia export format."""
    format_name = ParserFactory.detect_format(sample_insomnia_export)
    assert format_name == "insomnia"


def test_detect_openapi_spec(sample_openapi_spec):
    """Test detection of OpenAPI specification format."""
    format_name = ParserFactory.detect_format(sample_openapi_spec)
    assert format_name == "openapi"


def test_detect_format_from_string(sample_postman_collection):
    """Test format detection from JSON string."""
    json_string = json.dumps(sample_postman_collection)
    format_name = ParserFactory.detect_format(json_string)
    assert format_name == "postman"


def test_detect_unknown_format():
    """Test detection of unknown format."""
    unknown_data = {"random": "data", "format": "unknown"}
    format_name = ParserFactory.detect_format(unknown_data)
    assert format_name == "unknown"


def test_detect_invalid_json():
    """Test detection with invalid JSON."""
    format_name = ParserFactory.detect_format("invalid json")
    assert format_name == "unknown"


def test_detect_non_dict_data():
    """Test detection with non-dictionary data."""
    format_name = ParserFactory.detect_format(["not", "a", "dict"])
    assert format_name == "unknown"


def test_create_postman_parser(sample_postman_collection):
    """Test creating Postman parser."""
    parser = ParserFactory.create_parser(sample_postman_collection)
    assert isinstance(parser, PostmanParser)


def test_create_insomnia_parser(sample_insomnia_export):
    """Test creating Insomnia parser."""
    parser = ParserFactory.create_parser(sample_insomnia_export)
    assert isinstance(parser, InsomniaParser)


def test_create_openapi_parser(sample_openapi_spec):
    """Test creating OpenAPI parser."""
    parser = ParserFactory.create_parser(sample_openapi_spec)
    assert isinstance(parser, OpenAPIParser)


def test_create_parser_from_string(sample_postman_collection):
    """Test creating parser from JSON string."""
    json_string = json.dumps(sample_postman_collection)
    parser = ParserFactory.create_parser(json_string)
    assert isinstance(parser, PostmanParser)


def test_create_parser_unknown_format():
    """Test creating parser for unknown format."""
    unknown_data = {"random": "data"}
    parser = ParserFactory.create_parser(unknown_data)
    assert parser is None


def test_create_parser_invalid_json():
    """Test creating parser with invalid JSON."""
    parser = ParserFactory.create_parser("invalid json")
    assert parser is None


def test_validate_format_postman(sample_postman_collection):
    """Test format validation for Postman collection."""
    is_valid = ParserFactory.validate_format(sample_postman_collection, "postman")
    assert is_valid is True
    
    is_valid = ParserFactory.validate_format(sample_postman_collection, "insomnia")
    assert is_valid is False


def test_validate_format_insomnia(sample_insomnia_export):
    """Test format validation for Insomnia export."""
    is_valid = ParserFactory.validate_format(sample_insomnia_export, "insomnia")
    assert is_valid is True
    
    is_valid = ParserFactory.validate_format(sample_insomnia_export, "openapi")
    assert is_valid is False


def test_validate_format_openapi(sample_openapi_spec):
    """Test format validation for OpenAPI spec."""
    is_valid = ParserFactory.validate_format(sample_openapi_spec, "openapi")
    assert is_valid is True
    
    is_valid = ParserFactory.validate_format(sample_openapi_spec, "postman")
    assert is_valid is False


def test_detect_swagger_2_spec():
    """Test detection of Swagger 2.0 specification."""
    swagger_spec = {
        "swagger": "2.0",
        "info": {"title": "Swagger API", "version": "1.0.0"},
        "paths": {}
    }
    
    format_name = ParserFactory.detect_format(swagger_spec)
    assert format_name == "openapi"


def test_detect_minimal_openapi():
    """Test detection of minimal OpenAPI specification."""
    minimal_spec = {
        "paths": {},
        "info": {"title": "Minimal API", "version": "1.0.0"}
    }
    
    format_name = ParserFactory.detect_format(minimal_spec)
    assert format_name == "openapi"


def test_end_to_end_parsing_flow(sample_postman_collection):
    """Test complete parsing flow using factory."""
    # Detect format
    format_name = ParserFactory.detect_format(sample_postman_collection)
    assert format_name == "postman"
    
    # Create parser
    parser = ParserFactory.create_parser(sample_postman_collection)
    assert parser is not None
    
    # Parse specification
    spec = parser.parse(sample_postman_collection)
    assert spec.metadata.title == "Sample API Collection"
    
    # Validate specification
    errors = parser.validate(spec)
    assert len(errors) == 0


def test_factory_methods_consistency():
    """Test that factory methods are consistent with each other."""
    test_cases = [
        {
            "data": {
                "info": {"schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
                "item": []
            },
            "expected": "postman"
        },
        {
            "data": {
                "_type": "export",
                "__export_format": 4,
                "resources": []
            },
            "expected": "insomnia"
        },
        {
            "data": {
                "openapi": "3.0.0",
                "info": {"title": "Test", "version": "1.0.0"},
                "paths": {}
            },
            "expected": "openapi"
        }
    ]
    
    for case in test_cases:
        data = case["data"]
        expected = case["expected"]
        
        # Check detection
        detected = ParserFactory.detect_format(data)
        assert detected == expected
        
        # Check validation
        is_valid = ParserFactory.validate_format(data, expected)
        assert is_valid is True
        
        # Check parser creation
        parser = ParserFactory.create_parser(data)
        assert parser is not None