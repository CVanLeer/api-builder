"""
OpenAPI/Swagger parser implementation.

Parses OpenAPI 3.x and Swagger 2.0 specifications into unified APISpecification model.
Refactored from existing logic in dependency_analyzer.py.
"""

import json
from typing import Any, List, Union, Dict

from . import APISpecification, APIMetadata, AuthConfig, Endpoint, Parameter, Response


class OpenAPIParser:
    """Parser for OpenAPI 3.x and Swagger 2.0 specifications."""
    
    def parse(self, source: Union[str, dict]) -> APISpecification:
        """Parse OpenAPI specification into APISpecification."""
        if isinstance(source, str):
            try:
                spec_data = json.loads(source)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in OpenAPI spec: {e}")
        else:
            spec_data = source
            
        # Validate it's an OpenAPI/Swagger spec
        if not self._is_openapi_spec(spec_data):
            raise ValueError("Not a valid OpenAPI/Swagger specification")
            
        # Extract metadata
        info = spec_data.get("info", {})
        metadata = APIMetadata(
            title=info.get("title", "API"),
            version=info.get("version", "1.0.0"),
            description=info.get("description", ""),
            contact=info.get("contact", {}),
            license=info.get("license", {})
        )
        
        # Determine base URL
        base_url = self._extract_base_url(spec_data)
        if base_url:
            metadata.base_url = base_url
        
        # Extract authentication
        auth_config = self._parse_security(spec_data)
        
        # Extract schemas
        schemas = self._extract_schemas(spec_data)
        
        # Extract endpoints
        endpoints = []
        paths = spec_data.get("paths", {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.startswith("x-"):
                    continue  # Skip extensions
                if method in ["parameters", "summary", "description"]:
                    continue  # Skip non-operation fields
                    
                endpoint = self._parse_operation(path, method, operation, path_item, schemas)
                if endpoint:
                    endpoints.append(endpoint)
        
        return APISpecification(
            endpoints=endpoints,
            metadata=metadata,
            auth_config=auth_config,
            schemas=schemas
        )
    
    def validate(self, spec: APISpecification) -> List[str]:
        """Validate the parsed specification."""
        errors = []
        
        if not spec.endpoints:
            errors.append("No endpoints found in OpenAPI specification")
            
        for endpoint in spec.endpoints:
            if not endpoint.path:
                errors.append(f"Endpoint missing path: {endpoint.name}")
            if not endpoint.method:
                errors.append(f"Endpoint missing method: {endpoint.path}")
                
        return errors
    
    def _is_openapi_spec(self, data: dict) -> bool:
        """Check if the data is a valid OpenAPI/Swagger spec."""
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
    
    def _extract_base_url(self, spec_data: dict) -> str:
        """Extract base URL from the specification."""
        # OpenAPI 3.x servers
        servers = spec_data.get("servers", [])
        if servers and len(servers) > 0:
            return servers[0].get("url", "")
        
        # Swagger 2.0 format
        host = spec_data.get("host", "")
        base_path = spec_data.get("basePath", "")
        schemes = spec_data.get("schemes", ["https"])
        
        if host:
            scheme = schemes[0] if schemes else "https"
            return f"{scheme}://{host}{base_path}"
        
        return ""
    
    def _parse_security(self, spec_data: dict) -> AuthConfig:
        """Parse security/authentication configuration."""
        security_definitions = spec_data.get("securityDefinitions", {})
        components = spec_data.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        
        # Combine both formats
        all_security = {**security_definitions, **security_schemes}
        
        if not all_security:
            return AuthConfig(type="none")
        
        # Use the first security scheme found (simplified)
        scheme_name, scheme = next(iter(all_security.items()))
        
        scheme_type = scheme.get("type", "").lower()
        
        if scheme_type == "http":
            scheme_scheme = scheme.get("scheme", "").lower()
            if scheme_scheme == "bearer":
                return AuthConfig(type="bearer", location="header")
            elif scheme_scheme == "basic":
                return AuthConfig(type="basic", location="header")
        elif scheme_type == "apikey":
            return AuthConfig(
                type="apikey",
                location=scheme.get("in", "header"),
                name=scheme.get("name", "X-API-Key")
            )
        elif scheme_type == "oauth2":
            return AuthConfig(
                type="oauth2",
                flows=scheme.get("flows", {})
            )
        
        return AuthConfig(type=scheme_type)
    
    def _extract_schemas(self, spec_data: dict) -> dict:
        """Extract schema definitions."""
        # OpenAPI 3.x
        components = spec_data.get("components", {})
        schemas = components.get("schemas", {})
        
        # Swagger 2.0
        definitions = spec_data.get("definitions", {})
        
        return {**definitions, **schemas}
    
    def _parse_operation(
        self, 
        path: str, 
        method: str, 
        operation: dict, 
        path_item: dict,
        schemas: dict
    ) -> Endpoint:
        """Parse a single operation into an Endpoint."""
        name = operation.get("operationId", f"{method.upper()} {path}")
        description = operation.get("description", operation.get("summary", ""))
        tags = operation.get("tags", [])
        
        # Parse parameters
        parameters = []
        
        # Path-level parameters
        path_params = path_item.get("parameters", [])
        op_params = operation.get("parameters", [])
        all_params = path_params + op_params
        
        for param in all_params:
            # Handle parameter references
            if "$ref" in param:
                # Skip reference resolution for now
                continue
                
            param_name = param.get("name", "")
            param_in = param.get("in", "query")
            required = param.get("required", False)
            param_type = param.get("type", "string")
            description = param.get("description", "")
            
            # OpenAPI 3.x schema
            schema = param.get("schema", {})
            if schema:
                param_type = schema.get("type", "string")
            
            parameters.append(Parameter(
                name=param_name,
                location=param_in,
                required=required,
                type_info=param_type,
                description=description,
                example=param.get("example")
            ))
        
        # Parse request body (OpenAPI 3.x)
        request_body = None
        request_body_spec = operation.get("requestBody")
        if request_body_spec:
            content = request_body_spec.get("content", {})
            if content:
                # Use first content type
                content_type, content_spec = next(iter(content.items()))
                request_body = {
                    "type": "raw",
                    "content": content_spec.get("schema", {}),
                    "mimeType": content_type
                }
        
        # Parse responses
        responses = []
        responses_spec = operation.get("responses", {})
        for status_code, response_spec in responses_spec.items():
            try:
                status_int = int(status_code)
            except ValueError:
                continue
                
            description = response_spec.get("description", "")
            schema = None
            
            # Extract response schema
            content = response_spec.get("content", {})
            if content:
                # Use first content type
                content_type, content_spec = next(iter(content.items()))
                schema = content_spec.get("schema", {})
            else:
                # Swagger 2.0 format
                schema = response_spec.get("schema", {})
            
            responses.append(Response(
                status_code=status_int,
                description=description,
                schema=schema
            ))
        
        return Endpoint(
            path=path,
            method=method.upper(),
            name=name,
            description=description,
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            tags=tags
        )