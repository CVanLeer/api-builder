"""
Postman Collection v2.1 parser implementation.

Parses Postman collection format into unified APISpecification model.
"""

import json
from typing import Any, List, Union, Dict
from urllib.parse import urlparse, parse_qs

from . import APISpecification, APIMetadata, AuthConfig, Endpoint, Parameter, Response


class PostmanParser:
    """Parser for Postman Collection v2.1 format."""
    
    def parse(self, source: Union[str, dict]) -> APISpecification:
        """Parse Postman collection into APISpecification."""
        if isinstance(source, str):
            try:
                collection = json.loads(source)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in Postman collection: {e}")
        else:
            collection = source
            
        # Validate it's a Postman collection
        if not self._is_postman_collection(collection):
            raise ValueError("Not a valid Postman collection")
            
        # Extract metadata
        info = collection.get("info", {})
        metadata = APIMetadata(
            title=info.get("name", "Postman Collection"),
            version=info.get("version", "1.0.0"),
            description=info.get("description", ""),
        )
        
        # Extract authentication
        auth_config = self._parse_auth(collection.get("auth"))
        
        # Extract endpoints from items
        endpoints = []
        variables = {}
        
        # Process collection variables
        for var in collection.get("variable", []):
            variables[var.get("key", "")] = var.get("value", "")
            
        # Process items (requests)
        items = collection.get("item", [])
        self._process_items(items, endpoints, variables, "")
        
        return APISpecification(
            endpoints=endpoints,
            metadata=metadata,
            auth_config=auth_config,
            variables=variables
        )
    
    def validate(self, spec: APISpecification) -> List[str]:
        """Validate the parsed specification."""
        errors = []
        
        if not spec.endpoints:
            errors.append("No endpoints found in collection")
            
        for endpoint in spec.endpoints:
            if not endpoint.path:
                errors.append(f"Endpoint missing path: {endpoint.name}")
            if not endpoint.method:
                errors.append(f"Endpoint missing method: {endpoint.path}")
                
        return errors
    
    def _is_postman_collection(self, data: dict) -> bool:
        """Check if the data is a valid Postman collection."""
        info = data.get("info", {})
        schema = info.get("schema")
        return (
            isinstance(data, dict) and
            "info" in data and
            "item" in data and
            schema and
            "postman" in schema.lower()
        )
    
    def _parse_auth(self, auth_data: dict) -> AuthConfig:
        """Parse authentication configuration."""
        if not auth_data:
            return AuthConfig(type="none")
            
        auth_type = auth_data.get("type", "none")
        
        if auth_type == "bearer":
            return AuthConfig(
                type="bearer",
                location="header"
            )
        elif auth_type == "basic":
            return AuthConfig(
                type="basic",
                location="header"
            )
        elif auth_type == "apikey":
            apikey_data = auth_data.get("apikey", [])
            location = "header"
            name = "X-API-Key"
            
            for item in apikey_data:
                if item.get("key") == "in":
                    location = item.get("value", "header")
                elif item.get("key") == "key":
                    name = item.get("value", "X-API-Key")
                    
            return AuthConfig(
                type="apikey",
                location=location,
                name=name
            )
        elif auth_type == "oauth2":
            return AuthConfig(
                type="oauth2",
                flows=auth_data.get("oauth2", {})
            )
        else:
            return AuthConfig(type=auth_type)
    
    def _process_items(self, items: List[dict], endpoints: List[Endpoint], variables: dict, prefix: str):
        """Recursively process collection items (folders and requests)."""
        for item in items:
            if "item" in item:
                # This is a folder, process recursively
                folder_name = item.get("name", "")
                new_prefix = f"{prefix}/{folder_name}" if prefix else folder_name
                self._process_items(item["item"], endpoints, variables, new_prefix)
            else:
                # This is a request
                endpoint = self._parse_request(item, variables, prefix)
                if endpoint:
                    endpoints.append(endpoint)
    
    def _parse_request(self, request_item: dict, variables: dict, folder_path: str) -> Endpoint:
        """Parse a single request item into an Endpoint."""
        request = request_item.get("request", {})
        
        # Extract basic info
        name = request_item.get("name", "")
        description = request_item.get("description", "")
        method = request.get("method", "GET").upper()
        
        # Parse URL
        url_data = request.get("url", {})
        if isinstance(url_data, str):
            url = url_data
            path = urlparse(url).path
        else:
            # URL is an object
            raw_url = url_data.get("raw", "")
            path = "/".join(url_data.get("path", []))
            if not path.startswith("/"):
                path = "/" + path
        
        # Parse parameters
        parameters = []
        
        # Query parameters
        if isinstance(url_data, dict):
            query_params = url_data.get("query", [])
            for param in query_params:
                parameters.append(Parameter(
                    name=param.get("key", ""),
                    location="query",
                    required=not param.get("disabled", False),
                    description=param.get("description", ""),
                    example=param.get("value")
                ))
        
        # Path parameters (extract from path variables)
        if isinstance(url_data, dict):
            path_vars = url_data.get("variable", [])
            for var in path_vars:
                parameters.append(Parameter(
                    name=var.get("key", ""),
                    location="path", 
                    required=True,
                    description=var.get("description", ""),
                    example=var.get("value")
                ))
        
        # Header parameters
        headers = request.get("header", [])
        for header in headers:
            if not header.get("disabled", False):
                parameters.append(Parameter(
                    name=header.get("key", ""),
                    location="header",
                    required=True,
                    description=header.get("description", ""),
                    example=header.get("value")
                ))
        
        # Request body
        request_body = None
        body = request.get("body", {})
        if body:
            mode = body.get("mode")
            if mode == "raw":
                request_body = {
                    "type": "raw",
                    "content": body.get("raw", "")
                }
            elif mode == "formdata":
                request_body = {
                    "type": "formdata",
                    "fields": body.get("formdata", [])
                }
            elif mode == "urlencoded":
                request_body = {
                    "type": "urlencoded", 
                    "fields": body.get("urlencoded", [])
                }
        
        # Create responses (Postman doesn't have explicit response definitions)
        responses = [Response(status_code=200, description="Success")]
        
        # Tags from folder structure
        tags = [folder_path] if folder_path else []
        
        return Endpoint(
            path=path,
            method=method,
            name=name,
            description=description,
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            tags=tags
        )