"""
Parser factory for auto-detecting and creating appropriate parsers.

Automatically detects the format of API documentation and returns
the appropriate parser instance.
"""

import json
from typing import Any, Union, Optional

from . import Parser
from .postman import PostmanParser
from .insomnia import InsomniaParser


class ParserFactory:
    """Factory for creating appropriate parser based on input format."""
    
    @staticmethod
    def create_parser(source: Union[str, dict]) -> Optional[Parser]:
        """
        Auto-detect format and return appropriate parser.
        
        Args:
            source: Raw data to parse (string or dict)
            
        Returns:
            Parser instance or None if format not recognized
        """
        # Parse JSON if string
        if isinstance(source, str):
            try:
                data = json.loads(source)
            except json.JSONDecodeError:
                return None
        else:
            data = source
            
        if not isinstance(data, dict):
            return None
            
        # Check for Postman collection
        if ParserFactory._is_postman_collection(data):
            return PostmanParser()
            
        # Check for Insomnia export
        if ParserFactory._is_insomnia_export(data):
            return InsomniaParser()
            
        # Check for OpenAPI spec
        if ParserFactory._is_openapi_spec(data):
            # Import here to avoid circular dependency
            from .openapi import OpenAPIParser
            return OpenAPIParser()
            
        return None
    
    @staticmethod
    def detect_format(source: Union[str, dict]) -> str:
        """
        Detect the format of the input data.
        
        Args:
            source: Raw data to analyze
            
        Returns:
            Format name ('postman', 'insomnia', 'openapi', 'unknown')
        """
        # Parse JSON if string
        if isinstance(source, str):
            try:
                data = json.loads(source)
            except json.JSONDecodeError:
                return "unknown"
        else:
            data = source
            
        if not isinstance(data, dict):
            return "unknown"
            
        if ParserFactory._is_postman_collection(data):
            return "postman"
            
        if ParserFactory._is_insomnia_export(data):
            return "insomnia"
            
        if ParserFactory._is_openapi_spec(data):
            return "openapi"
            
        return "unknown"
    
    @staticmethod
    def _is_postman_collection(data: dict) -> bool:
        """Check if data is a Postman collection."""
        info = data.get("info", {})
        schema = info.get("schema", "")
        return (
            "info" in data and
            "item" in data and
            schema and
            "postman" in schema.lower()
        )
    
    @staticmethod
    def _is_insomnia_export(data: dict) -> bool:
        """Check if data is an Insomnia export."""
        return (
            data.get("_type") == "export" and
            "__export_format" in data and
            "resources" in data
        )
    
    @staticmethod
    def _is_openapi_spec(data: dict) -> bool:
        """Check if data is an OpenAPI specification."""
        # OpenAPI 3.x
        if "openapi" in data:
            return True
            
        # Swagger 2.0
        if "swagger" in data:
            return True
            
        # Additional heuristics
        if "paths" in data and "info" in data:
            return True
            
        return False
    
    @staticmethod
    def validate_format(source: Union[str, dict], expected_format: str) -> bool:
        """
        Validate that the source matches the expected format.
        
        Args:
            source: Raw data to validate
            expected_format: Expected format name
            
        Returns:
            True if format matches, False otherwise
        """
        detected = ParserFactory.detect_format(source)
        return detected == expected_format