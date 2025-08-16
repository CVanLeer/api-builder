"""
Insomnia export format v4 parser implementation.

Parses Insomnia workspace export into unified APISpecification model.
"""

import json
from typing import Any, List, Union, Dict
from urllib.parse import urlparse

from . import APISpecification, APIMetadata, AuthConfig, Endpoint, Parameter, Response


class InsomniaParser:
    """Parser for Insomnia export format v4."""
    
    def parse(self, source: Union[str, dict]) -> APISpecification:
        """Parse Insomnia export into APISpecification."""
        if isinstance(source, str):
            try:
                export_data = json.loads(source)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in Insomnia export: {e}")
        else:
            export_data = source
            
        # Validate it's an Insomnia export
        if not self._is_insomnia_export(export_data):
            raise ValueError("Not a valid Insomnia export")
            
        resources = export_data.get("resources", [])
        
        # Find workspace info
        workspace = None
        for resource in resources:
            if resource.get("_type") == "workspace":
                workspace = resource
                break
                
        # Extract metadata
        metadata = APIMetadata(
            title=workspace.get("name", "Insomnia Workspace") if workspace else "Insomnia Workspace",
            version="1.0.0",
            description=workspace.get("description", "") if workspace else "",
        )
        
        # Extract environment variables
        variables = {}
        for resource in resources:
            if resource.get("_type") == "environment":
                env_data = resource.get("data", {})
                variables.update(env_data)
        
        # Extract requests
        endpoints = []
        request_groups = {}  # For organizing into folders
        
        # First pass: collect request groups (folders)
        for resource in resources:
            if resource.get("_type") == "request_group":
                request_groups[resource.get("_id")] = resource.get("name", "")
        
        # Second pass: process requests
        for resource in resources:
            if resource.get("_type") == "request":
                endpoint = self._parse_request(resource, request_groups)
                if endpoint:
                    endpoints.append(endpoint)
        
        # Extract authentication (look for common auth patterns)
        auth_config = self._extract_auth_config(resources)
        
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
            errors.append("No requests found in Insomnia export")
            
        for endpoint in spec.endpoints:
            if not endpoint.path:
                errors.append(f"Request missing URL: {endpoint.name}")
            if not endpoint.method:
                errors.append(f"Request missing method: {endpoint.path}")
                
        return errors
    
    def _is_insomnia_export(self, data: dict) -> bool:
        """Check if the data is a valid Insomnia export."""
        return (
            isinstance(data, dict) and
            "_type" in data and
            data.get("_type") == "export" and
            "__export_format" in data and
            "resources" in data
        )
    
    def _extract_auth_config(self, resources: List[dict]) -> AuthConfig:
        """Extract authentication configuration from requests."""
        # Look for common authentication patterns across requests
        auth_types = set()
        
        for resource in resources:
            if resource.get("_type") == "request":
                auth = resource.get("authentication", {})
                auth_type = auth.get("type")
                if auth_type:
                    auth_types.add(auth_type)
        
        if not auth_types:
            return AuthConfig(type="none")
        
        # Use the most common auth type (simplified logic)
        auth_type = list(auth_types)[0]
        
        if auth_type == "bearer":
            return AuthConfig(type="bearer", location="header")
        elif auth_type == "basic":
            return AuthConfig(type="basic", location="header")
        elif auth_type == "oauth2":
            return AuthConfig(type="oauth2")
        else:
            return AuthConfig(type=auth_type)
    
    def _parse_request(self, request: dict, request_groups: Dict[str, str]) -> Endpoint:
        """Parse a single Insomnia request into an Endpoint."""
        name = request.get("name", "")
        description = request.get("description", "")
        method = request.get("method", "GET").upper()
        url = request.get("url", "")
        
        # Parse URL to get path
        if url:
            parsed = urlparse(url)
            path = parsed.path or "/"
        else:
            path = "/"
        
        # Parse parameters
        parameters = []
        
        # Query parameters
        for param in request.get("parameters", []):
            if not param.get("disabled", False):
                parameters.append(Parameter(
                    name=param.get("name", ""),
                    location="query",
                    required=not param.get("disabled", False),
                    description=param.get("description", ""),
                    example=param.get("value")
                ))
        
        # Headers
        for header in request.get("headers", []):
            if not header.get("disabled", False):
                parameters.append(Parameter(
                    name=header.get("name", ""),
                    location="header",
                    required=True,
                    description=header.get("description", ""),
                    example=header.get("value")
                ))
        
        # Request body
        request_body = None
        body = request.get("body", {})
        if body:
            mime_type = body.get("mimeType", "")
            text = body.get("text", "")
            
            if text:
                request_body = {
                    "type": "raw",
                    "content": text,
                    "mimeType": mime_type
                }
        
        # Create basic response (Insomnia doesn't define expected responses)
        responses = [Response(status_code=200, description="Success")]
        
        # Determine tags from parent group
        tags = []
        parent_id = request.get("parentId")
        if parent_id and parent_id in request_groups:
            tags.append(request_groups[parent_id])
        
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