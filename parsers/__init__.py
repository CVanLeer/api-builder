"""
API documentation parsers for various formats.

This module contains parsers that convert different API documentation
formats into our unified internal model.
"""

from typing import Protocol, Any, List
from dataclasses import dataclass


@dataclass
class Parameter:
    """API parameter definition."""
    name: str
    location: str  # path, query, header, body
    required: bool = False
    type_info: str = "string"
    description: str = ""
    example: Any = None


@dataclass
class Response:
    """API response definition."""
    status_code: int
    description: str = ""
    schema: dict = None
    examples: dict = None


@dataclass  
class Endpoint:
    """Single API endpoint definition."""
    path: str
    method: str
    name: str = ""
    description: str = ""
    parameters: List[Parameter] = None
    request_body: dict = None
    responses: List[Response] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.responses is None:
            self.responses = []
        if self.tags is None:
            self.tags = []


@dataclass
class AuthConfig:
    """Authentication configuration."""
    type: str  # none, basic, bearer, oauth2, apikey
    location: str = ""  # header, query (for apikey)
    name: str = ""  # key name (for apikey)
    flows: dict = None  # oauth2 flows
    
    def __post_init__(self):
        if self.flows is None:
            self.flows = {}


@dataclass
class APIMetadata:
    """API metadata information."""
    title: str = ""
    version: str = "1.0.0"
    description: str = ""
    base_url: str = ""
    contact: dict = None
    license: dict = None
    
    def __post_init__(self):
        if self.contact is None:
            self.contact = {}
        if self.license is None:
            self.license = {}


@dataclass
class APISpecification:
    """Unified internal API model."""
    endpoints: List[Endpoint]
    metadata: APIMetadata
    auth_config: AuthConfig = None
    schemas: dict = None
    variables: dict = None  # environment variables
    
    def __post_init__(self):
        if self.auth_config is None:
            self.auth_config = AuthConfig(type="none")
        if self.schemas is None:
            self.schemas = {}
        if self.variables is None:
            self.variables = {}


class Parser(Protocol):
    """Protocol for all API documentation parsers."""
    
    def parse(self, source: Any) -> APISpecification:
        """Parse the source into our internal model."""
        ...
    
    def validate(self, spec: APISpecification) -> List[str]:
        """Validate the parsed specification."""
        ...


# Export parsers and factory
from .postman import PostmanParser
from .insomnia import InsomniaParser  
from .openapi import OpenAPIParser
from .factory import ParserFactory

__all__ = [
    "APISpecification", "APIMetadata", "AuthConfig", "Endpoint", "Parameter", "Response",
    "Parser", "PostmanParser", "InsomniaParser", "OpenAPIParser", "ParserFactory"
]