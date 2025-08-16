"""
Custom exception hierarchy for API Builder.

This module provides a comprehensive set of exceptions for handling
various error scenarios in the API Builder application.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime


class APIError(Exception):
    """
    Base exception for all API-related errors.
    
    Attributes:
        message: Human-readable error message
        error_code: Optional error code for categorization
        details: Additional error details
        timestamp: When the error occurred
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_user_friendly_message(self) -> str:
        """Convert to a user-friendly error message."""
        return self.message


class APIConnectionError(APIError):
    """
    Raised when network connection to the API fails.
    
    Attributes:
        url: The URL that failed to connect
        timeout: Connection timeout if applicable
        retry_after: Suggested retry delay in seconds
    """
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        timeout: Optional[float] = None,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.url = url
        self.timeout = timeout
        self.retry_after = retry_after
        if url:
            self.details["url"] = url
        if timeout:
            self.details["timeout"] = timeout
        if retry_after:
            self.details["retry_after"] = retry_after
    
    def to_user_friendly_message(self) -> str:
        """Convert to user-friendly message with connection guidance."""
        base_msg = "Unable to reach the API. Please check your internet connection."
        if self.retry_after:
            base_msg += f" Try again in {self.retry_after} seconds."
        return base_msg


class AuthenticationError(APIError):
    """
    Raised when authentication fails.
    
    Attributes:
        auth_type: Type of authentication that failed
        retry_hints: Hints for retrying authentication
        requires_refresh: Whether token refresh might help
    """
    
    def __init__(
        self,
        message: str,
        auth_type: Optional[str] = None,
        retry_hints: Optional[List[str]] = None,
        requires_refresh: bool = False,
        **kwargs
    ):
        super().__init__(message, error_code="AUTH_FAILED", **kwargs)
        self.auth_type = auth_type
        self.retry_hints = retry_hints or []
        self.requires_refresh = requires_refresh
        self.details.update({
            "auth_type": auth_type,
            "retry_hints": retry_hints,
            "requires_refresh": requires_refresh
        })
    
    def to_user_friendly_message(self) -> str:
        """Convert to user-friendly authentication error message."""
        if self.requires_refresh:
            return "Authentication failed. Please run 'auth get-token' to refresh your credentials."
        if self.retry_hints:
            hints = " ".join(self.retry_hints)
            return f"Authentication failed. {hints}"
        return "Authentication failed. Please check your credentials and try again."


class RateLimitError(APIError):
    """
    Raised when API rate limit is exceeded.
    
    Attributes:
        retry_after: Time to wait before retrying (in seconds)
        limit: The rate limit that was exceeded
        remaining: Remaining requests in the window
        reset_at: When the rate limit resets
    """
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        remaining: int = 0,
        reset_at: Optional[datetime] = None,
        **kwargs
    ):
        super().__init__(message, error_code="RATE_LIMITED", **kwargs)
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining
        self.reset_at = reset_at
        self.details.update({
            "retry_after": retry_after,
            "limit": limit,
            "remaining": remaining,
            "reset_at": reset_at.isoformat() if reset_at else None
        })
    
    def to_user_friendly_message(self) -> str:
        """Convert to user-friendly rate limit message."""
        if self.retry_after:
            return f"Rate limit exceeded. Please wait {self.retry_after} seconds before retrying."
        if self.reset_at:
            return f"Rate limit exceeded. Limit resets at {self.reset_at.strftime('%H:%M:%S')}."
        return "Rate limit exceeded. Please wait a moment before retrying."


class ParseError(APIError):
    """
    Raised when parsing API responses or specifications fails.
    
    Attributes:
        source: What was being parsed
        line_number: Line number where parsing failed (if applicable)
        column: Column where parsing failed (if applicable)
        context: Surrounding context of the error
    """
    
    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        line_number: Optional[int] = None,
        column: Optional[int] = None,
        context: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="PARSE_ERROR", **kwargs)
        self.source = source
        self.line_number = line_number
        self.column = column
        self.context = context
        self.details.update({
            "source": source,
            "line_number": line_number,
            "column": column,
            "context": context
        })
    
    def to_user_friendly_message(self) -> str:
        """Convert to user-friendly parsing error message."""
        msg = "Failed to parse API response."
        if self.source:
            msg = f"Failed to parse {self.source}."
        if self.line_number:
            msg += f" Error at line {self.line_number}"
            if self.column:
                msg += f", column {self.column}"
        return msg


class ValidationError(APIError):
    """
    Raised when data validation fails.
    
    Attributes:
        field: The field that failed validation
        value: The invalid value
        expected_type: Expected type or format
        validation_errors: List of specific validation errors
    """
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        expected_type: Optional[str] = None,
        validation_errors: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        self.field = field
        self.value = value
        self.expected_type = expected_type
        self.validation_errors = validation_errors or []
        self.details.update({
            "field": field,
            "value": str(value) if value is not None else None,
            "expected_type": expected_type,
            "validation_errors": validation_errors
        })
    
    def to_user_friendly_message(self) -> str:
        """Convert to user-friendly validation error message."""
        if self.field:
            msg = f"Validation failed for field '{self.field}'."
            if self.expected_type:
                msg += f" Expected {self.expected_type}."
            return msg
        if self.validation_errors:
            error_count = len(self.validation_errors)
            return f"Validation failed with {error_count} error(s). Please check your input."
        return "Validation failed. Please check your input and try again."


class TimeoutError(APIError):
    """
    Raised when an operation times out.
    
    Attributes:
        operation: The operation that timed out
        timeout_seconds: The timeout duration
    """
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, error_code="TIMEOUT", **kwargs)
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        self.details.update({
            "operation": operation,
            "timeout_seconds": timeout_seconds
        })
    
    def to_user_friendly_message(self) -> str:
        """Convert to user-friendly timeout message."""
        if self.operation:
            return f"Operation '{self.operation}' timed out. The server may be slow or unresponsive."
        return "Request timed out. The server may be slow or unresponsive."


class CircuitBreakerError(APIError):
    """
    Raised when circuit breaker is open.
    
    Attributes:
        service: The service that's circuit-broken
        failure_count: Number of failures that triggered the breaker
        recovery_time: When the circuit breaker will attempt recovery
    """
    
    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        failure_count: Optional[int] = None,
        recovery_time: Optional[datetime] = None,
        **kwargs
    ):
        super().__init__(message, error_code="CIRCUIT_OPEN", **kwargs)
        self.service = service
        self.failure_count = failure_count
        self.recovery_time = recovery_time
        self.details.update({
            "service": service,
            "failure_count": failure_count,
            "recovery_time": recovery_time.isoformat() if recovery_time else None
        })
    
    def to_user_friendly_message(self) -> str:
        """Convert to user-friendly circuit breaker message."""
        if self.service:
            msg = f"Service '{self.service}' is temporarily unavailable due to repeated failures."
        else:
            msg = "Service temporarily unavailable due to repeated failures."
        
        if self.recovery_time:
            msg += f" Will retry at {self.recovery_time.strftime('%H:%M:%S')}."
        return msg


class ConfigurationError(APIError):
    """
    Raised when configuration is invalid or missing.
    
    Attributes:
        config_key: The configuration key that's problematic
        config_file: The configuration file involved
    """
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="CONFIG_ERROR", **kwargs)
        self.config_key = config_key
        self.config_file = config_file
        self.details.update({
            "config_key": config_key,
            "config_file": config_file
        })
    
    def to_user_friendly_message(self) -> str:
        """Convert to user-friendly configuration error message."""
        if self.config_key:
            return f"Configuration error: '{self.config_key}' is missing or invalid."
        if self.config_file:
            return f"Configuration error in file '{self.config_file}'."
        return "Configuration error. Please check your settings."


class RetryableError(APIError):
    """
    Base class for errors that can be retried.
    
    Attributes:
        can_retry: Whether the operation can be retried
        retry_count: Number of retries attempted
        max_retries: Maximum number of retries allowed
    """
    
    def __init__(
        self,
        message: str,
        can_retry: bool = True,
        retry_count: int = 0,
        max_retries: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.can_retry = can_retry
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.details.update({
            "can_retry": can_retry,
            "retry_count": retry_count,
            "max_retries": max_retries
        })
    
    def should_retry(self) -> bool:
        """Check if the operation should be retried."""
        if not self.can_retry:
            return False
        if self.max_retries is None:
            return True
        return self.retry_count < self.max_retries


def format_user_error(error: Exception) -> str:
    """
    Convert any exception to a user-friendly error message.
    
    Args:
        error: The exception to format
    
    Returns:
        A user-friendly error message
    """
    if isinstance(error, APIError):
        return error.to_user_friendly_message()
    
    # Handle standard Python exceptions
    error_mappings = {
        ConnectionError: "Unable to establish connection. Please check your network settings.",
        TimeoutError: "Operation timed out. Please try again.",
        PermissionError: "Permission denied. Please check your access rights.",
        FileNotFoundError: "Required file not found. Please check the file path.",
        ValueError: "Invalid input provided. Please check your parameters.",
        KeyError: "Required data not found. The API response may have changed.",
    }
    
    for error_type, message in error_mappings.items():
        if isinstance(error, error_type):
            return message
    
    # Default message for unknown errors
    return f"An unexpected error occurred: {str(error)}"