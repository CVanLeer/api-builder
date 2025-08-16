"""
Base utilities and common functionality for API parsers.

Provides shared utilities for validation, confidence scoring, and 
common parsing operations across different parser implementations.
"""

import re
import json
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import urlparse
import logging

from . import APISpecification, Endpoint, Parameter, ParameterType

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when API specification validation fails."""
    pass


class ParserError(Exception):
    """Raised when parsing fails."""
    pass


def calculate_confidence_score(source: Any, format_indicators: Dict[str, List[str]]) -> float:
    """
    Calculate confidence score for parsing a source.
    
    Args:
        source: The source data to analyze
        format_indicators: Dict mapping format names to lists of indicator strings
        
    Returns:
        Confidence score between 0.0 and 1.0
    """
    if not source:
        return 0.0
    
    source_str = str(source).lower()
    total_indicators = sum(len(indicators) for indicators in format_indicators.values())
    
    if total_indicators == 0:
        return 0.0
    
    matched_indicators = 0
    for format_name, indicators in format_indicators.items():
        for indicator in indicators:
            if indicator.lower() in source_str:
                matched_indicators += 1
    
    return min(matched_indicators / total_indicators, 1.0)


def validate_url(url: str) -> bool:
    """Validate if a string is a valid URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def validate_http_method(method: str) -> bool:
    """Validate if a string is a valid HTTP method."""
    valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
    return method.upper() in valid_methods


def validate_parameter_type(param_type: str) -> bool:
    """Validate if a string is a valid parameter type."""
    try:
        ParameterType(param_type.lower())
        return True
    except ValueError:
        return False


def validate_specification(spec: APISpecification) -> List[str]:
    """
    Validate an API specification and return list of validation errors.
    
    Args:
        spec: The APISpecification to validate
        
    Returns:
        List of validation error messages
    """
    errors = []
    
    # Validate info
    if not spec.info.title:
        errors.append("API title is required")
    
    if not spec.info.version:
        errors.append("API version is required")
    
    # Validate servers
    for i, server in enumerate(spec.servers):
        if not validate_url(server.url):
            errors.append(f"Server {i}: Invalid URL '{server.url}'")
    
    # Validate endpoints
    endpoint_paths = set()
    for i, endpoint in enumerate(spec.endpoints):
        # Check for duplicate paths with same method
        path_method = f"{endpoint.method.value}:{endpoint.path}"
        if path_method in endpoint_paths:
            errors.append(f"Endpoint {i}: Duplicate path-method combination '{path_method}'")
        endpoint_paths.add(path_method)
        
        # Validate path format
        if not endpoint.path.startswith('/'):
            errors.append(f"Endpoint {i}: Path must start with '/' but got '{endpoint.path}'")
        
        # Validate parameters
        param_names = set()
        for j, param in enumerate(endpoint.parameters):
            if param.name in param_names:
                errors.append(f"Endpoint {i}, Parameter {j}: Duplicate parameter name '{param.name}'")
            param_names.add(param.name)
            
            if not param.name:
                errors.append(f"Endpoint {i}, Parameter {j}: Parameter name cannot be empty")
        
        # Validate responses
        status_codes = set()
        for j, response in enumerate(endpoint.responses):
            if response.status_code in status_codes:
                errors.append(f"Endpoint {i}, Response {j}: Duplicate status code {response.status_code}")
            status_codes.add(response.status_code)
            
            if not (100 <= response.status_code <= 599):
                errors.append(f"Endpoint {i}, Response {j}: Invalid status code {response.status_code}")
    
    return errors


def normalize_path(path: str) -> str:
    """
    Normalize an API path by ensuring it starts with '/' and removing trailing '/'.
    
    Args:
        path: The path to normalize
        
    Returns:
        Normalized path
    """
    if not path:
        return "/"
    
    # Ensure path starts with '/'
    if not path.startswith('/'):
        path = '/' + path
    
    # Remove trailing '/' unless it's the root path
    if len(path) > 1 and path.endswith('/'):
        path = path.rstrip('/')
    
    return path


def extract_path_parameters(path: str) -> List[str]:
    """
    Extract parameter names from a path template.
    
    Supports both OpenAPI style {param} and other formats like :param or <param>.
    
    Args:
        path: The path template
        
    Returns:
        List of parameter names found in the path
    """
    # OpenAPI style: {param}
    openapi_params = re.findall(r'\{([^}]+)\}', path)
    
    # Express/Koa style: :param
    colon_params = re.findall(r':([a-zA-Z_][a-zA-Z0-9_]*)', path)
    
    # Flask style: <param>
    flask_params = re.findall(r'<([^>]+)>', path)
    
    # Combine all found parameters
    all_params = openapi_params + colon_params + flask_params
    
    # Remove duplicates while preserving order
    seen = set()
    unique_params = []
    for param in all_params:
        if param not in seen:
            seen.add(param)
            unique_params.append(param)
    
    return unique_params


def infer_parameter_type(name: str, value: Any = None) -> str:
    """
    Infer the data type of a parameter based on its name and optional value.
    
    Args:
        name: The parameter name
        value: Optional example value
        
    Returns:
        Inferred data type as string
    """
    name_lower = name.lower()
    
    # Check value first if provided
    if value is not None:
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        elif isinstance(value, str):
            # Try to infer more specific types for strings
            if re.match(r'^\d{4}-\d{2}-\d{2}', value):
                return "string"  # Could be date, but keep as string for now
            elif '@' in value and '.' in value:
                return "string"  # Could be email
            elif value.lower() in ('true', 'false'):
                return "boolean"
            return "string"
    
    # Infer from name patterns
    if any(keyword in name_lower for keyword in ['id', '_id', 'identifier']):
        return "integer"
    elif any(keyword in name_lower for keyword in ['count', 'size', 'limit', 'offset', 'page']):
        return "integer"
    elif any(keyword in name_lower for keyword in ['price', 'cost', 'amount', 'rate']):
        return "number"
    elif any(keyword in name_lower for keyword in ['email', 'mail']):
        return "string"
    elif any(keyword in name_lower for keyword in ['date', 'time', 'timestamp']):
        return "string"
    elif any(keyword in name_lower for keyword in ['is_', 'has_', 'enabled', 'disabled']):
        return "boolean"
    elif name_lower.endswith('s') and not name_lower.endswith('_s'):
        return "array"  # Plural names might be arrays
    else:
        return "string"  # Default fallback


def merge_specifications(specs: List[APISpecification]) -> APISpecification:
    """
    Merge multiple API specifications into one.
    
    Args:
        specs: List of APISpecification objects to merge
        
    Returns:
        Merged APISpecification
        
    Raises:
        ValueError: If specs list is empty
    """
    if not specs:
        raise ValueError("Cannot merge empty list of specifications")
    
    if len(specs) == 1:
        return specs[0]
    
    # Use first spec as base
    base_spec = specs[0]
    
    # Merge info (keep first spec's info, but combine descriptions)
    descriptions = [spec.info.description for spec in specs if spec.info.description]
    merged_description = " | ".join(descriptions) if descriptions else base_spec.info.description
    
    # Collect all unique servers
    all_servers = []
    seen_urls = set()
    for spec in specs:
        for server in spec.servers:
            if server.url not in seen_urls:
                all_servers.append(server)
                seen_urls.add(server.url)
    
    # Collect all unique endpoints
    all_endpoints = []
    seen_paths = set()
    for spec in specs:
        for endpoint in spec.endpoints:
            path_method = f"{endpoint.method.value}:{endpoint.path}"
            if path_method not in seen_paths:
                all_endpoints.append(endpoint)
                seen_paths.add(path_method)
    
    # Merge security schemes
    all_security_schemes = {}
    for spec in specs:
        all_security_schemes.update(spec.security_schemes)
    
    # Create merged specification
    merged_info = base_spec.info
    merged_info.description = merged_description
    
    return APISpecification(
        info=merged_info,
        servers=all_servers,
        endpoints=all_endpoints,
        security_schemes=all_security_schemes,
        components=base_spec.components,
        external_docs=base_spec.external_docs,
        source_format="merged",
        raw_data=None
    )


class BaseParser:
    """
    Base class with common parsing functionality.
    
    Not required by the Parser protocol, but provides useful defaults
    and utilities for concrete parser implementations.
    """
    
    def __init__(self, name: str, supported_formats: List[str]):
        self.name = name
        self._supported_formats = supported_formats
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @property
    def supported_formats(self) -> List[str]:
        """List of supported format identifiers."""
        return self._supported_formats
    
    def validate(self, spec: APISpecification) -> List[str]:
        """Validate the parsed specification."""
        return validate_specification(spec)
    
    def get_confidence_score(self, source: Any) -> float:
        """Get confidence score - subclasses should override with format-specific logic."""
        return 0.0
    
    def _log_parse_start(self, source_info: str):
        """Log the start of parsing."""
        self.logger.info(f"Starting to parse {source_info}")
    
    def _log_parse_complete(self, endpoints_count: int):
        """Log successful parsing completion."""
        self.logger.info(f"Successfully parsed {endpoints_count} endpoints")
    
    def _log_parse_error(self, error: str):
        """Log parsing error."""
        self.logger.error(f"Parsing failed: {error}")