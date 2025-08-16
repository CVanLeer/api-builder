"""
API documentation parsers for various formats.

This module contains parsers that convert different API documentation
formats into our unified internal model.
"""

from typing import Protocol, Any, List, Dict, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class HTTPMethod(Enum):
    """Supported HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ParameterType(Enum):
    """Parameter location types."""
    QUERY = "query"
    PATH = "path"
    HEADER = "header"
    BODY = "body"
    FORM = "form"


@dataclass
class Parameter:
    """API parameter definition."""
    name: str
    type: ParameterType
    data_type: str = "string"
    required: bool = False
    description: Optional[str] = None
    default: Optional[Any] = None
    example: Optional[Any] = None


@dataclass
class Response:
    """API response definition."""
    status_code: int
    description: Optional[str] = None
    content_type: str = "application/json"
    schema: Optional[Dict[str, Any]] = None
    examples: Optional[Dict[str, Any]] = None


@dataclass
class Endpoint:
    """API endpoint definition."""
    path: str
    method: HTTPMethod
    operation_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: List[Parameter] = field(default_factory=list)
    responses: List[Response] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    deprecated: bool = False


@dataclass
class Server:
    """API server definition."""
    url: str
    description: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None


@dataclass
class SecurityScheme:
    """API security scheme definition."""
    type: str
    scheme: Optional[str] = None
    bearer_format: Optional[str] = None
    name: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None


@dataclass
class Info:
    """API information."""
    title: str
    version: str = "1.0.0"
    description: Optional[str] = None
    terms_of_service: Optional[str] = None
    contact: Optional[Dict[str, str]] = None
    license: Optional[Dict[str, str]] = None


@dataclass
class APISpecification:
    """Unified internal API model."""
    info: Info
    servers: List[Server] = field(default_factory=list)
    endpoints: List[Endpoint] = field(default_factory=list)
    security_schemes: Dict[str, SecurityScheme] = field(default_factory=dict)
    components: Optional[Dict[str, Any]] = None
    external_docs: Optional[Dict[str, str]] = None
    source_format: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


class Parser(Protocol):
    """Protocol for all API documentation parsers."""
    
    def parse(self, source: Any) -> APISpecification:
        """Parse the source into our internal model."""
        ...
    
    def validate(self, spec: APISpecification) -> List[str]:
        """Validate the parsed specification."""
        ...
    
    def get_confidence_score(self, source: Any) -> float:
        """Get confidence score for parsing this source (0.0-1.0)."""
        ...
    
    @property
    def supported_formats(self) -> List[str]:
        """List of supported format identifiers."""
        ...


# Export public API
__all__ = [
    "APISpecification",
    "Parser", 
    "HTTPMethod",
    "ParameterType",
    "Parameter",
    "Response",
    "Endpoint",
    "Server",
    "SecurityScheme",
    "Info",
]