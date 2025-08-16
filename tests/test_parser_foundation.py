"""
Comprehensive tests for the parser foundation components.

Tests the APISpecification model, Parser protocol, and base utilities
to ensure the foundation is solid for building format-specific parsers.
"""

import pytest
from typing import Any, List
from unittest.mock import Mock

from parsers import (
    APISpecification, Parser, HTTPMethod, ParameterType,
    Parameter, Response, Endpoint, Server, SecurityScheme, Info
)
from parsers.base import (
    ValidationError, ParserError, BaseParser,
    calculate_confidence_score, validate_url, validate_http_method,
    validate_parameter_type, validate_specification, normalize_path,
    extract_path_parameters, infer_parameter_type, merge_specifications
)


class TestAPISpecificationModel:
    """Test the APISpecification dataclass and related models."""
    
    def test_info_creation(self):
        """Test Info model creation and defaults."""
        info = Info(title="Test API")
        assert info.title == "Test API"
        assert info.version == "1.0.0"  # Default version
        assert info.description is None
    
    def test_info_with_all_fields(self):
        """Test Info model with all optional fields."""
        info = Info(
            title="Test API",
            version="2.0.0",
            description="A test API",
            terms_of_service="https://example.com/terms",
            contact={"name": "API Team", "email": "api@example.com"},
            license={"name": "MIT", "url": "https://opensource.org/licenses/MIT"}
        )
        assert info.title == "Test API"
        assert info.version == "2.0.0"
        assert info.description == "A test API"
        assert info.contact["email"] == "api@example.com"
    
    def test_parameter_creation(self):
        """Test Parameter model creation."""
        param = Parameter(name="user_id", type=ParameterType.PATH)
        assert param.name == "user_id"
        assert param.type == ParameterType.PATH
        assert param.data_type == "string"  # Default
        assert param.required is False  # Default
    
    def test_parameter_with_all_fields(self):
        """Test Parameter model with all fields."""
        param = Parameter(
            name="limit",
            type=ParameterType.QUERY,
            data_type="integer",
            required=True,
            description="Maximum number of results",
            default=10,
            example=25
        )
        assert param.name == "limit"
        assert param.type == ParameterType.QUERY
        assert param.data_type == "integer"
        assert param.required is True
        assert param.default == 10
        assert param.example == 25
    
    def test_response_creation(self):
        """Test Response model creation."""
        response = Response(status_code=200)
        assert response.status_code == 200
        assert response.content_type == "application/json"  # Default
        assert response.description is None
    
    def test_endpoint_creation(self):
        """Test Endpoint model creation."""
        endpoint = Endpoint(path="/users", method=HTTPMethod.GET)
        assert endpoint.path == "/users"
        assert endpoint.method == HTTPMethod.GET
        assert endpoint.parameters == []  # Default empty list
        assert endpoint.responses == []  # Default empty list
        assert endpoint.deprecated is False  # Default
    
    def test_endpoint_with_parameters_and_responses(self):
        """Test Endpoint model with parameters and responses."""
        param = Parameter(name="id", type=ParameterType.PATH, required=True)
        response = Response(status_code=200, description="Success")
        
        endpoint = Endpoint(
            path="/users/{id}",
            method=HTTPMethod.GET,
            parameters=[param],
            responses=[response],
            summary="Get user by ID"
        )
        assert len(endpoint.parameters) == 1
        assert endpoint.parameters[0].name == "id"
        assert len(endpoint.responses) == 1
        assert endpoint.responses[0].status_code == 200
        assert endpoint.summary == "Get user by ID"
    
    def test_server_creation(self):
        """Test Server model creation."""
        server = Server(url="https://api.example.com")
        assert server.url == "https://api.example.com"
        assert server.description is None
        assert server.variables is None
    
    def test_security_scheme_creation(self):
        """Test SecurityScheme model creation."""
        scheme = SecurityScheme(type="http", scheme="bearer")
        assert scheme.type == "http"
        assert scheme.scheme == "bearer"
        assert scheme.bearer_format is None
    
    def test_api_specification_creation(self):
        """Test APISpecification model creation."""
        info = Info(title="Test API", version="1.0.0")
        spec = APISpecification(info=info)
        
        assert spec.info.title == "Test API"
        assert spec.servers == []  # Default empty list
        assert spec.endpoints == []  # Default empty list
        assert spec.security_schemes == {}  # Default empty dict
        assert spec.source_format is None
    
    def test_api_specification_with_all_fields(self):
        """Test APISpecification model with all fields populated."""
        info = Info(title="Test API", version="1.0.0")
        server = Server(url="https://api.example.com")
        endpoint = Endpoint(path="/users", method=HTTPMethod.GET)
        security_scheme = SecurityScheme(type="http", scheme="bearer")
        
        spec = APISpecification(
            info=info,
            servers=[server],
            endpoints=[endpoint],
            security_schemes={"bearerAuth": security_scheme},
            source_format="openapi",
            raw_data={"openapi": "3.0.0"}
        )
        
        assert len(spec.servers) == 1
        assert spec.servers[0].url == "https://api.example.com"
        assert len(spec.endpoints) == 1
        assert spec.endpoints[0].path == "/users"
        assert "bearerAuth" in spec.security_schemes
        assert spec.source_format == "openapi"
        assert spec.raw_data["openapi"] == "3.0.0"


class TestEnums:
    """Test the enum classes."""
    
    def test_http_method_enum(self):
        """Test HTTPMethod enum values."""
        assert HTTPMethod.GET.value == "GET"
        assert HTTPMethod.POST.value == "POST"
        assert HTTPMethod.PUT.value == "PUT"
        assert HTTPMethod.DELETE.value == "DELETE"
        assert HTTPMethod.PATCH.value == "PATCH"
        assert HTTPMethod.HEAD.value == "HEAD"
        assert HTTPMethod.OPTIONS.value == "OPTIONS"
    
    def test_parameter_type_enum(self):
        """Test ParameterType enum values."""
        assert ParameterType.QUERY.value == "query"
        assert ParameterType.PATH.value == "path"
        assert ParameterType.HEADER.value == "header"
        assert ParameterType.BODY.value == "body"
        assert ParameterType.FORM.value == "form"


class TestParserProtocol:
    """Test the Parser protocol interface."""
    
    def test_parser_protocol_methods(self):
        """Test that Parser protocol defines expected methods."""
        # Create a mock parser implementing the protocol
        parser = Mock(spec=Parser)
        
        # Verify the protocol methods exist
        assert hasattr(parser, 'parse')
        assert hasattr(parser, 'validate')
        assert hasattr(parser, 'get_confidence_score')
        assert hasattr(parser, 'supported_formats')


class TestBaseUtilities:
    """Test the base utility functions."""
    
    def test_calculate_confidence_score(self):
        """Test confidence score calculation."""
        format_indicators = {
            "openapi": ["openapi", "swagger"],
            "postman": ["collection", "postman"]
        }
        
        # Empty source
        assert calculate_confidence_score("", format_indicators) == 0.0
        
        # No indicators found
        assert calculate_confidence_score("random text", format_indicators) == 0.0
        
        # Some indicators found
        source = "This is an openapi specification"
        score = calculate_confidence_score(source, format_indicators)
        assert 0.0 < score <= 1.0
        
        # All indicators found
        source = "openapi swagger collection postman"
        score = calculate_confidence_score(source, format_indicators)
        assert score == 1.0
    
    def test_validate_url(self):
        """Test URL validation."""
        assert validate_url("https://api.example.com") is True
        assert validate_url("http://localhost:8080") is True
        assert validate_url("not-a-url") is False
        assert validate_url("") is False
        assert validate_url("ftp://example.com") is True  # Different scheme but still valid URL
    
    def test_validate_http_method(self):
        """Test HTTP method validation."""
        assert validate_http_method("GET") is True
        assert validate_http_method("get") is True  # Case insensitive
        assert validate_http_method("POST") is True
        assert validate_http_method("INVALID") is False
        assert validate_http_method("") is False
    
    def test_validate_parameter_type(self):
        """Test parameter type validation."""
        assert validate_parameter_type("query") is True
        assert validate_parameter_type("QUERY") is True  # Case insensitive
        assert validate_parameter_type("path") is True
        assert validate_parameter_type("invalid") is False
        assert validate_parameter_type("") is False
    
    def test_normalize_path(self):
        """Test path normalization."""
        assert normalize_path("users") == "/users"
        assert normalize_path("/users") == "/users"
        assert normalize_path("/users/") == "/users"
        assert normalize_path("") == "/"
        assert normalize_path("/") == "/"
        assert normalize_path("users/{id}/posts") == "/users/{id}/posts"
    
    def test_extract_path_parameters(self):
        """Test path parameter extraction."""
        # OpenAPI style
        assert extract_path_parameters("/users/{id}") == ["id"]
        assert extract_path_parameters("/users/{id}/posts/{post_id}") == ["id", "post_id"]
        
        # Express style
        assert extract_path_parameters("/users/:id") == ["id"]
        
        # Flask style
        assert extract_path_parameters("/users/<id>") == ["id"]
        
        # Mixed styles
        assert extract_path_parameters("/users/{id}/posts/:post_id") == ["id", "post_id"]
        
        # No parameters
        assert extract_path_parameters("/users") == []
        
        # Duplicate parameters (should deduplicate)
        assert extract_path_parameters("/users/{id}/duplicate/{id}") == ["id"]
    
    def test_infer_parameter_type(self):
        """Test parameter type inference."""
        # From value
        assert infer_parameter_type("test", 42) == "integer"
        assert infer_parameter_type("test", 3.14) == "number"
        assert infer_parameter_type("test", True) == "boolean"
        assert infer_parameter_type("test", "hello") == "string"
        assert infer_parameter_type("test", [1, 2, 3]) == "array"
        assert infer_parameter_type("test", {"key": "value"}) == "object"
        
        # From name patterns
        assert infer_parameter_type("user_id") == "integer"
        assert infer_parameter_type("count") == "integer"
        assert infer_parameter_type("price") == "number"
        assert infer_parameter_type("email") == "string"
        assert infer_parameter_type("is_active") == "boolean"
        assert infer_parameter_type("tags") == "array"
        assert infer_parameter_type("random_name") == "string"  # Default


class TestValidateSpecification:
    """Test the specification validation function."""
    
    def test_valid_specification(self):
        """Test validation of a valid specification."""
        info = Info(title="Test API", version="1.0.0")
        server = Server(url="https://api.example.com")
        param = Parameter(name="id", type=ParameterType.PATH, required=True)
        response = Response(status_code=200, description="Success")
        endpoint = Endpoint(
            path="/users/{id}",
            method=HTTPMethod.GET,
            parameters=[param],
            responses=[response]
        )
        
        spec = APISpecification(
            info=info,
            servers=[server],
            endpoints=[endpoint]
        )
        
        errors = validate_specification(spec)
        assert errors == []
    
    def test_missing_title(self):
        """Test validation with missing title."""
        info = Info(title="", version="1.0.0")
        spec = APISpecification(info=info)
        
        errors = validate_specification(spec)
        assert "API title is required" in errors
    
    def test_missing_version(self):
        """Test validation with missing version."""
        info = Info(title="Test API", version="")
        spec = APISpecification(info=info)
        
        errors = validate_specification(spec)
        assert "API version is required" in errors
    
    def test_invalid_server_url(self):
        """Test validation with invalid server URL."""
        info = Info(title="Test API", version="1.0.0")
        server = Server(url="not-a-url")
        spec = APISpecification(info=info, servers=[server])
        
        errors = validate_specification(spec)
        assert any("Invalid URL" in error for error in errors)
    
    def test_duplicate_endpoints(self):
        """Test validation with duplicate endpoints."""
        info = Info(title="Test API", version="1.0.0")
        endpoint1 = Endpoint(path="/users", method=HTTPMethod.GET)
        endpoint2 = Endpoint(path="/users", method=HTTPMethod.GET)
        spec = APISpecification(info=info, endpoints=[endpoint1, endpoint2])
        
        errors = validate_specification(spec)
        assert any("Duplicate path-method combination" in error for error in errors)
    
    def test_invalid_path_format(self):
        """Test validation with invalid path format."""
        info = Info(title="Test API", version="1.0.0")
        endpoint = Endpoint(path="users", method=HTTPMethod.GET)  # Missing leading slash
        spec = APISpecification(info=info, endpoints=[endpoint])
        
        errors = validate_specification(spec)
        assert any("Path must start with '/'" in error for error in errors)
    
    def test_duplicate_parameters(self):
        """Test validation with duplicate parameters."""
        info = Info(title="Test API", version="1.0.0")
        param1 = Parameter(name="id", type=ParameterType.PATH)
        param2 = Parameter(name="id", type=ParameterType.QUERY)
        endpoint = Endpoint(path="/users/{id}", method=HTTPMethod.GET, parameters=[param1, param2])
        spec = APISpecification(info=info, endpoints=[endpoint])
        
        errors = validate_specification(spec)
        assert any("Duplicate parameter name" in error for error in errors)
    
    def test_invalid_status_code(self):
        """Test validation with invalid status codes."""
        info = Info(title="Test API", version="1.0.0")
        response1 = Response(status_code=999)  # Invalid
        response2 = Response(status_code=200)
        response3 = Response(status_code=200)  # Duplicate
        endpoint = Endpoint(path="/users", method=HTTPMethod.GET, responses=[response1, response2, response3])
        spec = APISpecification(info=info, endpoints=[endpoint])
        
        errors = validate_specification(spec)
        assert any("Invalid status code 999" in error for error in errors)
        assert any("Duplicate status code 200" in error for error in errors)


class TestMergeSpecifications:
    """Test the merge specifications functionality."""
    
    def test_merge_empty_list_raises_error(self):
        """Test that merging empty list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot merge empty list"):
            merge_specifications([])
    
    def test_merge_single_specification(self):
        """Test merging a single specification returns it unchanged."""
        info = Info(title="Test API", version="1.0.0")
        spec = APISpecification(info=info)
        
        result = merge_specifications([spec])
        assert result is spec
    
    def test_merge_multiple_specifications(self):
        """Test merging multiple specifications."""
        # First spec
        info1 = Info(title="API 1", version="1.0.0", description="First API")
        server1 = Server(url="https://api1.example.com")
        endpoint1 = Endpoint(path="/users", method=HTTPMethod.GET)
        spec1 = APISpecification(info=info1, servers=[server1], endpoints=[endpoint1])
        
        # Second spec
        info2 = Info(title="API 2", version="1.0.0", description="Second API")
        server2 = Server(url="https://api2.example.com")
        endpoint2 = Endpoint(path="/posts", method=HTTPMethod.GET)
        spec2 = APISpecification(info=info2, servers=[server2], endpoints=[endpoint2])
        
        # Merge
        result = merge_specifications([spec1, spec2])
        
        # Check merged result
        assert result.info.title == "API 1"  # Uses first spec's title
        assert "First API | Second API" in result.info.description
        assert len(result.servers) == 2
        assert len(result.endpoints) == 2
        assert result.source_format == "merged"
        
        # Verify no duplicates
        server_urls = [s.url for s in result.servers]
        assert "https://api1.example.com" in server_urls
        assert "https://api2.example.com" in server_urls
    
    def test_merge_handles_duplicates(self):
        """Test that merging handles duplicate servers and endpoints."""
        info = Info(title="Test API", version="1.0.0")
        server = Server(url="https://api.example.com")
        endpoint = Endpoint(path="/users", method=HTTPMethod.GET)
        
        spec1 = APISpecification(info=info, servers=[server], endpoints=[endpoint])
        spec2 = APISpecification(info=info, servers=[server], endpoints=[endpoint])  # Same server and endpoint
        
        result = merge_specifications([spec1, spec2])
        
        # Should deduplicate
        assert len(result.servers) == 1
        assert len(result.endpoints) == 1


class TestBaseParser:
    """Test the BaseParser class."""
    
    def test_base_parser_creation(self):
        """Test BaseParser instantiation."""
        parser = BaseParser("test", ["format1", "format2"])
        assert parser.name == "test"
        assert parser.supported_formats == ["format1", "format2"]
    
    def test_base_parser_validate(self):
        """Test BaseParser validation uses the validate_specification function."""
        parser = BaseParser("test", ["format1"])
        info = Info(title="Test API", version="1.0.0")
        spec = APISpecification(info=info)
        
        errors = parser.validate(spec)
        assert errors == []  # Should be valid
    
    def test_base_parser_confidence_score_default(self):
        """Test BaseParser confidence score returns default 0.0."""
        parser = BaseParser("test", ["format1"])
        assert parser.get_confidence_score("anything") == 0.0
    
    def test_base_parser_logging_methods(self):
        """Test BaseParser logging methods don't raise errors."""
        parser = BaseParser("test", ["format1"])
        
        # These should not raise exceptions
        parser._log_parse_start("test source")
        parser._log_parse_complete(5)
        parser._log_parse_error("test error")


class TestExceptions:
    """Test custom exception classes."""
    
    def test_validation_error(self):
        """Test ValidationError can be raised and caught."""
        with pytest.raises(ValidationError):
            raise ValidationError("Validation failed")
    
    def test_parser_error(self):
        """Test ParserError can be raised and caught."""
        with pytest.raises(ParserError):
            raise ParserError("Parsing failed")


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])