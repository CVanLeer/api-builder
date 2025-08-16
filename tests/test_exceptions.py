"""
Unit tests for custom exceptions module.
"""

import pytest
from datetime import datetime, timedelta
from qapi.exceptions import (
    APIError,
    APIConnectionError,
    AuthenticationError,
    RateLimitError,
    ParseError,
    ValidationError,
    TimeoutError,
    CircuitBreakerError,
    ConfigurationError,
    RetryableError,
    format_user_error
)


class TestAPIError:
    """Test base APIError class."""
    
    def test_api_error_creation(self):
        error = APIError("Test error", error_code="TEST_ERROR", details={"key": "value"})
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.details == {"key": "value"}
        assert isinstance(error.timestamp, datetime)
    
    def test_api_error_to_dict(self):
        error = APIError("Test error", error_code="TEST_ERROR")
        error_dict = error.to_dict()
        assert error_dict["error_type"] == "APIError"
        assert error_dict["message"] == "Test error"
        assert error_dict["error_code"] == "TEST_ERROR"
        assert "timestamp" in error_dict
    
    def test_api_error_user_friendly_message(self):
        error = APIError("Technical error message")
        assert error.to_user_friendly_message() == "Technical error message"


class TestAPIConnectionError:
    """Test APIConnectionError class."""
    
    def test_connection_error_with_url(self):
        error = APIConnectionError(
            "Connection failed",
            url="https://api.example.com",
            timeout=30.0
        )
        assert error.url == "https://api.example.com"
        assert error.timeout == 30.0
        assert error.details["url"] == "https://api.example.com"
        assert error.details["timeout"] == 30.0
    
    def test_connection_error_with_retry_after(self):
        error = APIConnectionError(
            "Connection failed",
            retry_after=60
        )
        assert error.retry_after == 60
        assert "Try again in 60 seconds" in error.to_user_friendly_message()
    
    def test_connection_error_user_friendly_message(self):
        error = APIConnectionError("Failed to connect")
        expected = "Unable to reach the API. Please check your internet connection."
        assert error.to_user_friendly_message() == expected


class TestAuthenticationError:
    """Test AuthenticationError class."""
    
    def test_auth_error_with_refresh_required(self):
        error = AuthenticationError(
            "Token expired",
            auth_type="Bearer",
            requires_refresh=True
        )
        assert error.auth_type == "Bearer"
        assert error.requires_refresh is True
        expected = "Authentication failed. Please run 'auth get-token' to refresh your credentials."
        assert error.to_user_friendly_message() == expected
    
    def test_auth_error_with_retry_hints(self):
        error = AuthenticationError(
            "Invalid credentials",
            retry_hints=["Check your API key.", "Ensure correct permissions."]
        )
        assert len(error.retry_hints) == 2
        expected = "Authentication failed. Check your API key. Ensure correct permissions."
        assert error.to_user_friendly_message() == expected
    
    def test_auth_error_default_message(self):
        error = AuthenticationError("Auth failed")
        expected = "Authentication failed. Please check your credentials and try again."
        assert error.to_user_friendly_message() == expected


class TestRateLimitError:
    """Test RateLimitError class."""
    
    def test_rate_limit_with_retry_after(self):
        error = RateLimitError(
            "Rate limit exceeded",
            retry_after=120,
            limit=100,
            remaining=0
        )
        assert error.retry_after == 120
        assert error.limit == 100
        assert error.remaining == 0
        expected = "Rate limit exceeded. Please wait 120 seconds before retrying."
        assert error.to_user_friendly_message() == expected
    
    def test_rate_limit_with_reset_time(self):
        reset_time = datetime.utcnow() + timedelta(minutes=5)
        error = RateLimitError(
            "Rate limit exceeded",
            reset_at=reset_time
        )
        assert error.reset_at == reset_time
        assert "Limit resets at" in error.to_user_friendly_message()
    
    def test_rate_limit_default_message(self):
        error = RateLimitError("Too many requests")
        expected = "Rate limit exceeded. Please wait a moment before retrying."
        assert error.to_user_friendly_message() == expected


class TestParseError:
    """Test ParseError class."""
    
    def test_parse_error_with_location(self):
        error = ParseError(
            "Invalid JSON",
            source="response.json",
            line_number=10,
            column=15,
            context='{"invalid": '
        )
        assert error.source == "response.json"
        assert error.line_number == 10
        assert error.column == 15
        assert error.context == '{"invalid": '
        expected = "Failed to parse response.json. Error at line 10, column 15"
        assert error.to_user_friendly_message() == expected
    
    def test_parse_error_with_source_only(self):
        error = ParseError("Parse failed", source="config.yaml")
        assert error.to_user_friendly_message() == "Failed to parse config.yaml."
    
    def test_parse_error_default_message(self):
        error = ParseError("Parse failed")
        assert error.to_user_friendly_message() == "Failed to parse API response."


class TestValidationError:
    """Test ValidationError class."""
    
    def test_validation_error_with_field(self):
        error = ValidationError(
            "Invalid value",
            field="email",
            value="invalid-email",
            expected_type="email format"
        )
        assert error.field == "email"
        assert error.value == "invalid-email"
        assert error.expected_type == "email format"
        expected = "Validation failed for field 'email'. Expected email format."
        assert error.to_user_friendly_message() == expected
    
    def test_validation_error_with_multiple_errors(self):
        validation_errors = [
            {"field": "email", "error": "Invalid format"},
            {"field": "age", "error": "Must be positive"}
        ]
        error = ValidationError(
            "Multiple validation errors",
            validation_errors=validation_errors
        )
        assert len(error.validation_errors) == 2
        expected = "Validation failed with 2 error(s). Please check your input."
        assert error.to_user_friendly_message() == expected
    
    def test_validation_error_default_message(self):
        error = ValidationError("Validation failed")
        expected = "Validation failed. Please check your input and try again."
        assert error.to_user_friendly_message() == expected


class TestTimeoutError:
    """Test TimeoutError class."""
    
    def test_timeout_error_with_operation(self):
        error = TimeoutError(
            "Request timed out",
            operation="API call",
            timeout_seconds=30.0
        )
        assert error.operation == "API call"
        assert error.timeout_seconds == 30.0
        expected = "Operation 'API call' timed out. The server may be slow or unresponsive."
        assert error.to_user_friendly_message() == expected
    
    def test_timeout_error_default_message(self):
        error = TimeoutError("Timed out")
        expected = "Request timed out. The server may be slow or unresponsive."
        assert error.to_user_friendly_message() == expected


class TestCircuitBreakerError:
    """Test CircuitBreakerError class."""
    
    def test_circuit_breaker_error_with_service(self):
        recovery_time = datetime.utcnow() + timedelta(seconds=60)
        error = CircuitBreakerError(
            "Circuit open",
            service="payment-api",
            failure_count=5,
            recovery_time=recovery_time
        )
        assert error.service == "payment-api"
        assert error.failure_count == 5
        assert error.recovery_time == recovery_time
        message = error.to_user_friendly_message()
        assert "payment-api" in message
        assert "temporarily unavailable" in message
    
    def test_circuit_breaker_error_default_message(self):
        error = CircuitBreakerError("Circuit open")
        expected = "Service temporarily unavailable due to repeated failures."
        assert error.to_user_friendly_message() == expected


class TestConfigurationError:
    """Test ConfigurationError class."""
    
    def test_config_error_with_key(self):
        error = ConfigurationError(
            "Missing config",
            config_key="API_KEY"
        )
        assert error.config_key == "API_KEY"
        expected = "Configuration error: 'API_KEY' is missing or invalid."
        assert error.to_user_friendly_message() == expected
    
    def test_config_error_with_file(self):
        error = ConfigurationError(
            "Invalid config",
            config_file="config.json"
        )
        assert error.config_file == "config.json"
        expected = "Configuration error in file 'config.json'."
        assert error.to_user_friendly_message() == expected
    
    def test_config_error_default_message(self):
        error = ConfigurationError("Config error")
        expected = "Configuration error. Please check your settings."
        assert error.to_user_friendly_message() == expected


class TestRetryableError:
    """Test RetryableError class."""
    
    def test_retryable_error_can_retry(self):
        error = RetryableError("Temporary failure", can_retry=True)
        assert error.can_retry is True
        assert error.should_retry() is True
    
    def test_retryable_error_max_retries(self):
        error = RetryableError(
            "Temporary failure",
            retry_count=2,
            max_retries=3
        )
        assert error.should_retry() is True
        
        error.retry_count = 3
        assert error.should_retry() is False
    
    def test_retryable_error_cannot_retry(self):
        error = RetryableError("Permanent failure", can_retry=False)
        assert error.should_retry() is False


class TestFormatUserError:
    """Test format_user_error function."""
    
    def test_format_api_error(self):
        error = APIConnectionError("Connection failed")
        message = format_user_error(error)
        assert "Unable to reach the API" in message
    
    def test_format_standard_connection_error(self):
        error = ConnectionError("Network error")
        message = format_user_error(error)
        assert "Unable to establish connection" in message
    
    def test_format_permission_error(self):
        error = PermissionError("Access denied")
        message = format_user_error(error)
        assert "Permission denied" in message
    
    def test_format_file_not_found_error(self):
        error = FileNotFoundError("File missing")
        message = format_user_error(error)
        assert "Required file not found" in message
    
    def test_format_value_error(self):
        error = ValueError("Invalid input")
        message = format_user_error(error)
        assert "Invalid input provided" in message
    
    def test_format_key_error(self):
        error = KeyError("missing_key")
        message = format_user_error(error)
        assert "Required data not found" in message
    
    def test_format_unknown_error(self):
        error = RuntimeError("Something went wrong")
        message = format_user_error(error)
        assert "An unexpected error occurred: Something went wrong" == message