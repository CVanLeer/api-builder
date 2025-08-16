"""
Comprehensive unit tests for ParameterDetector module.
Achieving 90%+ coverage for all methods and edge cases.
"""
import pytest
from typing import Dict, Any, List
from cli.parameter_detector import (
    ParameterDetector, 
    ParameterType, 
    ParameterInfo
)


class TestParameterType:
    """Test the ParameterType enum."""
    
    def test_parameter_type_values(self):
        """Test that all parameter types are defined."""
        assert ParameterType.FOREIGN_KEY
        assert ParameterType.ENUM
        assert ParameterType.DATE
        assert ParameterType.DATETIME
        assert ParameterType.PAGINATION
        assert ParameterType.FILTER
        assert ParameterType.SORT
        assert ParameterType.SEARCH
        assert ParameterType.BOOLEAN
        assert ParameterType.NUMERIC
        assert ParameterType.STRING
        assert ParameterType.UNKNOWN


class TestParameterInfo:
    """Test the ParameterInfo dataclass."""
    
    def test_parameter_info_creation(self):
        """Test creating ParameterInfo instances."""
        info = ParameterInfo(
            name="testParam",
            type=ParameterType.STRING,
            likely_provider="test_endpoint",
            is_required=True,
            schema_type="string",
            enum_values=["a", "b"],
            pattern="^[a-z]+$"
        )
        
        assert info.name == "testParam"
        assert info.type == ParameterType.STRING
        assert info.likely_provider == "test_endpoint"
        assert info.is_required is True
        assert info.schema_type == "string"
        assert info.enum_values == ["a", "b"]
        assert info.pattern == "^[a-z]+$"
    
    def test_parameter_info_defaults(self):
        """Test default values for optional fields."""
        info = ParameterInfo(
            name="test",
            type=ParameterType.UNKNOWN
        )
        
        assert info.likely_provider is None
        assert info.is_required is False
        assert info.schema_type is None
        assert info.enum_values is None
        assert info.pattern is None


class TestParameterDetector:
    """Test suite for ParameterDetector class."""
    
    @pytest.fixture
    def detector(self) -> ParameterDetector:
        """Create a ParameterDetector instance."""
        return ParameterDetector()
    
    @pytest.fixture
    def sample_schemas(self, sample_parameter_schemas) -> Dict[str, Any]:
        """Use sample schemas from conftest."""
        return sample_parameter_schemas
    
    def test_initialization(self, detector):
        """Test ParameterDetector initialization."""
        assert detector.id_patterns
        assert detector.reference_patterns
        assert detector.pagination_params
        assert detector.date_patterns
        assert detector.filter_patterns
        
        # Check some specific patterns
        assert "merchantId" in detector.reference_patterns
        assert detector.reference_patterns["merchantId"] == "merchants"
        assert "page" in detector.pagination_params
    
    def test_detect_enum_parameter(self, detector, sample_schemas):
        """Test detection of enum parameters."""
        schema = sample_schemas["status"]
        info = detector.detect_parameter_type("status", schema)
        
        assert info.type == ParameterType.ENUM
        assert info.enum_values == ["pending", "completed", "cancelled"]
        assert info.name == "status"
    
    def test_detect_foreign_key_parameter(self, detector, sample_schemas):
        """Test detection of foreign key parameters."""
        # Test merchantId
        schema = sample_schemas["merchantId"]
        info = detector.detect_parameter_type("merchantId", schema)
        
        assert info.type == ParameterType.FOREIGN_KEY
        assert info.likely_provider == "merchants"
        
        # Test customerId
        schema = sample_schemas["customerId"]
        info = detector.detect_parameter_type("customerId", schema)
        
        assert info.type == ParameterType.FOREIGN_KEY
        assert info.likely_provider == "customers"
    
    def test_detect_pagination_parameters(self, detector, sample_schemas):
        """Test detection of pagination parameters."""
        # Test page
        schema = sample_schemas["page"]
        info = detector.detect_parameter_type("page", schema)
        
        assert info.type == ParameterType.PAGINATION
        
        # Test pageSize
        schema = sample_schemas["pageSize"]
        info = detector.detect_parameter_type("pageSize", schema)
        
        assert info.type == ParameterType.PAGINATION
    
    def test_detect_date_parameters(self, detector, sample_schemas):
        """Test detection of date/datetime parameters."""
        schema = sample_schemas["startDate"]
        info = detector.detect_parameter_type("startDate", schema)
        
        assert info.type == ParameterType.DATE
        
        # Test datetime detection
        datetime_schema = {
            "name": "createdDateTime",
            "type": "string",
            "format": "date-time"
        }
        info = detector.detect_parameter_type("createdDateTime", datetime_schema)
        
        assert info.type == ParameterType.DATETIME
    
    def test_detect_search_filter_parameters(self, detector, sample_schemas):
        """Test detection of search and filter parameters."""
        # Test search
        schema = sample_schemas["search"]
        info = detector.detect_parameter_type("search", schema)
        
        assert info.type == ParameterType.SEARCH
        
        # Test filter
        filter_schema = {"name": "filterBy", "type": "string"}
        info = detector.detect_parameter_type("filterBy", filter_schema)
        
        assert info.type == ParameterType.FILTER
    
    def test_detect_boolean_parameter(self, detector, sample_schemas):
        """Test detection of boolean parameters."""
        schema = sample_schemas["isActive"]
        info = detector.detect_parameter_type("isActive", schema)
        
        assert info.type == ParameterType.BOOLEAN
        assert info.schema_type == "boolean"
    
    def test_detect_numeric_parameters(self, detector):
        """Test detection of numeric parameters."""
        # Integer
        int_schema = {"name": "count", "type": "integer"}
        info = detector.detect_parameter_type("count", int_schema)
        
        assert info.type == ParameterType.NUMERIC
        
        # Number (float)
        float_schema = {"name": "price", "type": "number"}
        info = detector.detect_parameter_type("price", float_schema)
        
        assert info.type == ParameterType.NUMERIC
    
    def test_detect_string_parameter(self, detector):
        """Test detection of string parameters."""
        schema = {"name": "name", "type": "string"}
        info = detector.detect_parameter_type("name", schema)
        
        assert info.type == ParameterType.STRING
        assert info.schema_type == "string"
    
    def test_detect_parameter_with_pattern(self, detector, sample_schemas):
        """Test detection of parameters with patterns."""
        schema = sample_schemas["customerId"]
        info = detector.detect_parameter_type("customerId", schema)
        
        assert info.pattern == "^[a-zA-Z0-9-]+$"
    
    def test_is_foreign_key(self, detector):
        """Test is_foreign_key method."""
        # Should match
        assert detector.is_foreign_key("userId") is True
        assert detector.is_foreign_key("merchantId") is True
        assert detector.is_foreign_key("customer_id") is True
        assert detector.is_foreign_key("orderIds") is True
        assert detector.is_foreign_key("UUID") is True
        assert detector.is_foreign_key("id") is True
        assert detector.is_foreign_key("ID") is True
        
        # Should not match
        assert detector.is_foreign_key("name") is False
        assert detector.is_foreign_key("email") is False
        assert detector.is_foreign_key("description") is False
        assert detector.is_foreign_key("") is False
    
    def test_get_likely_provider(self, detector):
        """Test get_likely_provider method."""
        # Direct matches
        assert detector.get_likely_provider("merchantId") == "merchants"
        assert detector.get_likely_provider("locationId") == "locations"
        assert detector.get_likely_provider("userId") == "users"
        
        # Case-insensitive matches
        assert detector.get_likely_provider("MerchantId") == "merchants"
        assert detector.get_likely_provider("MERCHANTID") == "merchants"
        
        # Inferred matches
        assert detector.get_likely_provider("customerId") == "customers"
        assert detector.get_likely_provider("productId") == "products"
        assert detector.get_likely_provider("categoryId") == "categorys"  # Simple pluralization
        
        # No match for non-FK
        assert detector.get_likely_provider("name") is None
        assert detector.get_likely_provider("email") is None
    
    def test_extract_id_from_response_direct(self, detector):
        """Test extracting ID from response - direct match."""
        response = {
            "merchantId": "merch-123",
            "name": "Test Merchant"
        }
        
        result = detector.extract_id_from_response(response, "merchantId")
        assert result == "merch-123"
    
    def test_extract_id_from_response_data_wrapper(self, detector):
        """Test extracting ID from response with data wrapper."""
        # Single object in data
        response = {
            "data": {
                "merchantId": "merch-456",
                "name": "Test"
            }
        }
        result = detector.extract_id_from_response(response, "merchantId")
        assert result == "merch-456"
        
        # Array in data - should return first item
        response = {
            "data": [
                {"merchantId": "merch-789", "name": "First"},
                {"merchantId": "merch-000", "name": "Second"}
            ]
        }
        result = detector.extract_id_from_response(response, "merchantId")
        assert result == "merch-789"
    
    def test_extract_id_from_response_case_variations(self, detector):
        """Test extracting ID with case variations."""
        response = {
            "merchant_id": "merch-123"
        }
        
        # Should find snake_case version
        result = detector.extract_id_from_response(response, "merchantId")
        assert result == "merch-123"
        
        # Test other variations
        response = {
            "MERCHANTID": "merch-upper"
        }
        result = detector.extract_id_from_response(response, "merchantId")
        assert result == "merch-upper"
    
    def test_extract_id_from_response_nested(self, detector):
        """Test extracting ID from nested response."""
        response = {
            "result": {
                "data": {
                    "merchantId": "nested-123"
                }
            }
        }
        
        result = detector.extract_id_from_response(response, "merchantId")
        assert result == "nested-123"
    
    def test_extract_id_from_response_any_id(self, detector):
        """Test extracting any ID field when specific not found."""
        response = {
            "id": "generic-123",
            "name": "Test"
        }
        
        # Should find generic 'id' field for foreign key params
        result = detector.extract_id_from_response(response, "merchantId")
        assert result == "generic-123"
    
    def test_extract_id_from_response_not_found(self, detector):
        """Test extracting ID when not found."""
        response = {
            "name": "Test",
            "email": "test@example.com"
        }
        
        result = detector.extract_id_from_response(response, "merchantId")
        assert result is None
        
        # Non-FK parameter should also return None
        result = detector.extract_id_from_response(response, "description")
        assert result is None
    
    def test_get_parameter_metadata(self, detector):
        """Test extracting parameter metadata."""
        schema = {
            "name": "test",
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
            "default": 10,
            "description": "Test parameter",
            "format": "int32",
            "multipleOf": 5
        }
        
        metadata = detector.get_parameter_metadata(schema)
        
        assert metadata["minimum"] == 1
        assert metadata["maximum"] == 100
        assert metadata["default"] == 10
        assert metadata["description"] == "Test parameter"
        assert metadata["format"] == "int32"
        assert metadata["multipleOf"] == 5
    
    def test_get_parameter_metadata_string_constraints(self, detector):
        """Test metadata extraction for string constraints."""
        schema = {
            "name": "test",
            "type": "string",
            "minLength": 3,
            "maxLength": 50,
            "pattern": "^[a-z]+$"
        }
        
        metadata = detector.get_parameter_metadata(schema)
        
        assert metadata["minLength"] == 3
        assert metadata["maxLength"] == 50
        assert "pattern" not in metadata  # pattern is handled separately
    
    def test_get_parameter_metadata_array_constraints(self, detector):
        """Test metadata extraction for array constraints."""
        schema = {
            "name": "test",
            "type": "array",
            "minItems": 1,
            "maxItems": 10
        }
        
        metadata = detector.get_parameter_metadata(schema)
        
        assert metadata["minItems"] == 1
        assert metadata["maxItems"] == 10
    
    def test_get_parameter_metadata_empty(self, detector):
        """Test metadata extraction with no constraints."""
        schema = {
            "name": "test",
            "type": "string"
        }
        
        metadata = detector.get_parameter_metadata(schema)
        
        assert metadata == {}
    
    def test_matches_patterns(self, detector):
        """Test _matches_patterns method."""
        import re
        
        patterns = [
            re.compile(r'.*Id$'),
            re.compile(r'^id$', re.I)
        ]
        
        assert detector._matches_patterns("userId", patterns) is True
        assert detector._matches_patterns("id", patterns) is True
        assert detector._matches_patterns("ID", patterns) is True
        assert detector._matches_patterns("name", patterns) is False
    
    def test_find_nested_value(self, detector):
        """Test _find_nested_value method."""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "target": "found"
                    }
                }
            }
        }
        
        # Should find at depth 3
        result = detector._find_nested_value(data, "target", max_depth=3)
        assert result == "found"
        
        # Should not find beyond max depth
        result = detector._find_nested_value(data, "target", max_depth=2)
        assert result is None
        
        # Should find at top level
        data["target"] = "top"
        result = detector._find_nested_value(data, "target", max_depth=1)
        assert result == "top"
    
    def test_find_any_id_field(self, detector):
        """Test _find_any_id_field method."""
        # Simple case
        data = {"id": "123", "name": "test"}
        result = detector._find_any_id_field(data)
        assert result == "123"
        
        # Field ending with 'id'
        data = {"customerId": "456", "name": "test"}
        result = detector._find_any_id_field(data)
        assert result == "456"
        
        # Nested in data wrapper
        data = {
            "data": {
                "userId": "789"
            }
        }
        result = detector._find_any_id_field(data)
        assert result == "789"
        
        # Array in data wrapper
        data = {
            "data": [
                {"orderId": "001"},
                {"orderId": "002"}
            ]
        }
        result = detector._find_any_id_field(data)
        assert result == "001"
        
        # No ID field
        data = {"name": "test", "email": "test@example.com"}
        result = detector._find_any_id_field(data)
        assert result is None
    
    def test_camel_to_snake(self, detector):
        """Test _camel_to_snake conversion."""
        assert detector._camel_to_snake("merchantId") == "merchant_id"
        assert detector._camel_to_snake("MerchantId") == "merchant_id"
        assert detector._camel_to_snake("merchantID") == "merchant_i_d"
        assert detector._camel_to_snake("simple") == "simple"
        assert detector._camel_to_snake("") == ""
    
    def test_snake_to_camel(self, detector):
        """Test _snake_to_camel conversion."""
        assert detector._snake_to_camel("merchant_id") == "merchantId"
        assert detector._snake_to_camel("user_profile_id") == "userProfileId"
        assert detector._snake_to_camel("simple") == "simple"
        assert detector._snake_to_camel("") == ""
    
    def test_complex_parameter_detection(self, detector):
        """Test detection with complex parameter schemas."""
        # Parameter with multiple indicators
        schema = {
            "name": "StartDateUtc",
            "type": "string",
            "format": "date-time",
            "required": True,
            "description": "Start date in UTC"
        }
        
        info = detector.detect_parameter_type("StartDateUtc", schema)
        
        # Should detect as datetime due to format
        assert info.type == ParameterType.DATETIME
        assert info.is_required is True
    
    def test_edge_cases(self, detector):
        """Test edge cases and unusual inputs."""
        # Empty schema
        info = detector.detect_parameter_type("test", {})
        assert info.type == ParameterType.UNKNOWN
        assert info.schema_type is None
        
        # None values in schema
        schema = {
            "name": None,
            "type": None,
            "required": None
        }
        info = detector.detect_parameter_type("test", schema)
        assert info.type == ParameterType.UNKNOWN
        
        # Unknown type
        schema = {"type": "custom_type"}
        info = detector.detect_parameter_type("test", schema)
        assert info.type == ParameterType.UNKNOWN