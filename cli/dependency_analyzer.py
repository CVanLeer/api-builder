from typing import Dict, List, Set
import re


class DependencyAnalyzer:
    """
    Analyzes an OpenAPI specification to build a dependency graph for endpoint
    parameters. Detects parameter providers, foreign key patterns, schema
    references, and nested properties.
    """
    def __init__(self, openapi_spec: dict):
        """
        Initialize the analyzer with a loaded OpenAPI spec.
        :param openapi_spec: The OpenAPI specification as a dictionary.
        """
        self.spec = openapi_spec
        self.paths = self.spec.get("paths", {})
        self.components = self.spec.get("components", {})
        self.schemas = self.components.get("schemas", {})
        self.param_to_providers = self.analyze_parameters()
        self.dependency_graph = self.build_dependency_graph()

    def analyze_parameters(self) -> Dict[str, List[str]]:
        """
        Analyze all parameters in the OpenAPI spec and map them to provider
        endpoints. Returns a dict mapping parameter names to a list of endpoint
        paths that can provide them.
        """
        param_providers: Dict[str, List[str]] = {}
        for path, methods in self.paths.items():
            for method, details in methods.items():
                # Only consider GET endpoints for now
                if method.lower() != "get":
                    continue
                # Check response schemas for parameters
                responses = details.get("responses", {})
                for resp in responses.values():
                    content = resp.get("content", {})
                    for media, media_obj in content.items():
                        schema = media_obj.get("schema", {})
                        # Handle $ref or inline schema
                        props = self._extract_properties(schema)
                        for prop in props:
                            param_providers.setdefault(prop, []).append(path)
                        # Also check for nested properties
                        for nested in self._extract_nested_properties(schema):
                            param_providers.setdefault(nested, []).append(path)
                # Smart detection for foreign key patterns
                for param in details.get("parameters", []):
                    name = param.get("name", "")
                    if self._is_foreign_key(name):
                        param_providers.setdefault(name, []).append(path)
        return param_providers

    def find_parameter_providers(self, param_name: str) -> List[str]:
        """
        Find all endpoints that can provide the given parameter.
        :param param_name: The parameter name to search for.
        :return: List of endpoint paths that return this parameter.
        """
        return self.param_to_providers.get(param_name, [])

    def build_dependency_graph(self) -> Dict[str, Set[str]]:
        """
        Build a dependency graph where each endpoint points to the parameters it
        requires and the endpoints that can provide them.
        :return: Dict mapping endpoint paths to sets of dependent endpoint paths.
        """
        graph: Dict[str, Set[str]] = {}
        for path, methods in self.paths.items():
            for method, details in methods.items():
                if method.lower() != "get":
                    continue
                required_params = [
                    p.get("name") for p in details.get("parameters", [])
                    if p.get("required")
                ]
                deps = set()
                for param in required_params:
                    providers = self.find_parameter_providers(param)
                    deps.update(providers)
                graph[path] = deps - {path}  # Remove self-dependency
        return graph

    def get_execution_plan(
        self, target_endpoint: str, required_params: List[str]
    ) -> List[str]:
        """
        Given a target endpoint and required parameters, return an ordered list
        of endpoints to call to satisfy all dependencies (topological order).
        :param target_endpoint: The endpoint path to call last.
        :param required_params: List of parameter names required by the target
        endpoint.
        :return: Ordered list of endpoint paths to call.
        """
        plan = []
        visited = set()

        def visit(endpoint: str):
            if endpoint in visited:
                return
            visited.add(endpoint)
            for dep in self.dependency_graph.get(endpoint, []):
                visit(dep)
            plan.append(endpoint)

        # Start with providers for each required param
        for param in required_params:
            for provider in self.find_parameter_providers(param):
                visit(provider)
        visit(target_endpoint)
        # Remove duplicates while preserving order
        seen = set()
        ordered = []
        for ep in plan:
            if ep not in seen:
                ordered.append(ep)
                seen.add(ep)
        return ordered

    def _extract_properties(self, schema: dict) -> Set[str]:
        """
        Extract top-level property names from a schema, following $ref if present.
        """
        props = set()
        if "$ref" in schema:
            ref = schema["$ref"].split("/")[-1]
            schema = self.schemas.get(ref, {})
        for k, v in schema.get("properties", {}).items():
            props.add(k)
        return props

    def _extract_nested_properties(self, schema: dict) -> Set[str]:
        """
        Recursively extract nested property names from a schema.
        """
        nested = set()
        if "$ref" in schema:
            ref = schema["$ref"].split("/")[-1]
            schema = self.schemas.get(ref, {})
        for k, v in schema.get("properties", {}).items():
            if v.get("type") == "object":
                nested.update(self._extract_properties(v))
            if (
                v.get("type") == "array"
                and "items" in v
            ):
                nested.update(
                    self._extract_properties(v["items"])
                )
        return nested

    def _is_foreign_key(self, name: str) -> bool:
        """
        Detect if a parameter name looks like a foreign key (e.g., ends with 'Id').
        """
        return bool(re.match(r".*Id$", name)) 