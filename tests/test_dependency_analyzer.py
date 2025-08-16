"""
Comprehensive unit tests for DependencyAnalyzer module.
Achieving 90%+ coverage for all methods and edge cases.
"""
import pytest
from typing import Dict, List, Set, Any
from cli.dependency_analyzer import DependencyAnalyzer


class TestDependencyAnalyzer:
    """Test suite for DependencyAnalyzer class."""
    
    @pytest.fixture
    def simple_spec(self) -> Dict[str, Any]:
        """Simple OpenAPI spec for basic testing."""
        return {
            "paths": {
                "/users": {
                    "get": {
                        "parameters": [],
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "properties": {
                                                "userId": {"type": "string"},
                                                "name": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/posts": {
                    "get": {
                        "parameters": [
                            {"name": "userId", "required": True}
                        ],
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "properties": {
                                                "postId": {"type": "string"},
                                                "title": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "components": {
                "schemas": {}
            }
        }
    
    @pytest.fixture
    def complex_spec(self, sample_openapi_spec) -> Dict[str, Any]:
        """Use the complex spec from conftest."""
        return sample_openapi_spec
    
    @pytest.fixture
    def spec_with_refs(self) -> Dict[str, Any]:
        """OpenAPI spec with $ref references."""
        return {
            "paths": {
                "/items": {
                    "get": {
                        "parameters": [],
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/ItemList"
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/items/{itemId}": {
                    "get": {
                        "parameters": [
                            {"name": "itemId", "required": True}
                        ],
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/Item"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "components": {
                "schemas": {
                    "ItemList": {
                        "type": "object",
                        "properties": {
                            "items": {
                                "type": "array",
                                "items": {
                                    "$ref": "#/components/schemas/Item"
                                }
                            }
                        }
                    },
                    "Item": {
                        "type": "object",
                        "properties": {
                            "itemId": {"type": "string"},
                            "name": {"type": "string"},
                            "categoryId": {"type": "string"},
                            "metadata": {
                                "type": "object",
                                "properties": {
                                    "tags": {"type": "array"},
                                    "rating": {"type": "number"}
                                }
                            }
                        }
                    }
                }
            }
        }
    
    @pytest.fixture
    def spec_with_nested(self) -> Dict[str, Any]:
        """OpenAPI spec with nested properties."""
        return {
            "paths": {
                "/complex": {
                    "get": {
                        "parameters": [],
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "properties": {
                                                "id": {"type": "string"},
                                                "data": {
                                                    "type": "object",
                                                    "properties": {
                                                        "nestedId": {"type": "string"},
                                                        "details": {
                                                            "type": "object",
                                                            "properties": {
                                                                "deepId": {"type": "string"}
                                                            }
                                                        }
                                                    }
                                                },
                                                "items": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {
                                                            "arrayItemId": {"type": "string"}
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "components": {"schemas": {}}
        }
    
    def test_initialization(self, simple_spec):
        """Test DependencyAnalyzer initialization."""
        analyzer = DependencyAnalyzer(simple_spec)
        
        assert analyzer.spec == simple_spec
        assert analyzer.paths == simple_spec["paths"]
        assert analyzer.components == simple_spec["components"]
        assert analyzer.schemas == {}
        assert isinstance(analyzer.param_to_providers, dict)
        assert isinstance(analyzer.dependency_graph, dict)
    
    def test_initialization_with_schemas(self, spec_with_refs):
        """Test initialization with schemas in components."""
        analyzer = DependencyAnalyzer(spec_with_refs)
        
        assert "ItemList" in analyzer.schemas
        assert "Item" in analyzer.schemas
        assert analyzer.schemas["Item"]["properties"]["itemId"]["type"] == "string"
    
    def test_analyze_parameters_basic(self, simple_spec):
        """Test basic parameter analysis."""
        analyzer = DependencyAnalyzer(simple_spec)
        
        # Check that userId is recognized as a provider from /users
        assert "userId" in analyzer.param_to_providers
        assert "/users" in analyzer.param_to_providers["userId"]
        assert "name" in analyzer.param_to_providers
        assert "/users" in analyzer.param_to_providers["name"]
    
    def test_analyze_parameters_with_refs(self, spec_with_refs):
        """Test parameter analysis with $ref resolution."""
        analyzer = DependencyAnalyzer(spec_with_refs)
        
        # Should resolve refs and find properties
        assert "itemId" in analyzer.param_to_providers
        assert "/items" in analyzer.param_to_providers["itemId"]
        assert "categoryId" in analyzer.param_to_providers
    
    def test_analyze_parameters_nested_properties(self, spec_with_nested):
        """Test parameter analysis with nested properties."""
        analyzer = DependencyAnalyzer(spec_with_nested)
        
        # Should find nested properties
        assert "nestedId" in analyzer.param_to_providers
        assert "arrayItemId" in analyzer.param_to_providers
        assert "/complex" in analyzer.param_to_providers["nestedId"]
    
    def test_analyze_parameters_non_get_methods(self):
        """Test that non-GET methods are ignored."""
        spec = {
            "paths": {
                "/users": {
                    "post": {
                        "responses": {
                            "201": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "properties": {
                                                "userId": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "get": {
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "properties": {
                                                "userId": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "components": {"schemas": {}}
        }
        
        analyzer = DependencyAnalyzer(spec)
        # Only GET method should be considered
        assert "userId" in analyzer.param_to_providers
        assert analyzer.param_to_providers["userId"] == ["/users"]
    
    def test_foreign_key_detection(self):
        """Test foreign key pattern detection."""
        spec = {
            "paths": {
                "/orders": {
                    "get": {
                        "parameters": [
                            {"name": "customerId", "required": True},
                            {"name": "storeId", "required": False}
                        ],
                        "responses": {"200": {"content": {}}}
                    }
                }
            },
            "components": {"schemas": {}}
        }
        
        analyzer = DependencyAnalyzer(spec)
        # Foreign key parameters should be detected
        assert "customerId" in analyzer.param_to_providers
        assert "storeId" in analyzer.param_to_providers
    
    def test_find_parameter_providers(self, simple_spec):
        """Test finding providers for a specific parameter."""
        analyzer = DependencyAnalyzer(simple_spec)
        
        providers = analyzer.find_parameter_providers("userId")
        assert providers == ["/users"]
        
        providers = analyzer.find_parameter_providers("nonexistent")
        assert providers == []
    
    def test_build_dependency_graph(self, simple_spec):
        """Test building the dependency graph."""
        analyzer = DependencyAnalyzer(simple_spec)
        
        # /posts depends on userId which is provided by /users
        assert "/posts" in analyzer.dependency_graph
        assert "/users" in analyzer.dependency_graph["/posts"]
        
        # /users has no dependencies
        assert "/users" in analyzer.dependency_graph
        assert len(analyzer.dependency_graph["/users"]) == 0
    
    def test_build_dependency_graph_complex(self, complex_spec):
        """Test dependency graph with complex relationships."""
        analyzer = DependencyAnalyzer(complex_spec)
        
        # /locations depends on merchantId
        assert "/locations" in analyzer.dependency_graph
        assert "/merchants" in analyzer.dependency_graph["/locations"]
        
        # /orders depends on locationId
        assert "/orders" in analyzer.dependency_graph
        assert "/locations" in analyzer.dependency_graph["/orders"]
    
    def test_build_dependency_graph_no_self_dependency(self):
        """Test that endpoints don't depend on themselves."""
        spec = {
            "paths": {
                "/items": {
                    "get": {
                        "parameters": [
                            {"name": "itemId", "required": False}
                        ],
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "properties": {
                                                "itemId": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "components": {"schemas": {}}
        }
        
        analyzer = DependencyAnalyzer(spec)
        # /items should not depend on itself even though it provides itemId
        assert "/items" not in analyzer.dependency_graph["/items"]
    
    def test_get_execution_plan_simple(self, simple_spec):
        """Test execution plan generation for simple dependencies."""
        analyzer = DependencyAnalyzer(simple_spec)
        
        plan = analyzer.get_execution_plan("/posts", ["userId"])
        # Should call /users first to get userId, then /posts
        assert plan == ["/users", "/posts"]
    
    def test_get_execution_plan_complex(self, complex_spec):
        """Test execution plan with multi-level dependencies."""
        analyzer = DependencyAnalyzer(complex_spec)
        
        plan = analyzer.get_execution_plan("/orders", ["locationId"])
        # Should include /locations and its dependencies
        assert "/locations" in plan
        assert "/orders" in plan
        assert plan.index("/locations") < plan.index("/orders")
    
    def test_get_execution_plan_no_duplicates(self, complex_spec):
        """Test that execution plan has no duplicates."""
        analyzer = DependencyAnalyzer(complex_spec)
        
        plan = analyzer.get_execution_plan("/orders", ["locationId"])
        # Check no duplicates
        assert len(plan) == len(set(plan))
    
    def test_get_execution_plan_circular_dependency(self):
        """Test handling of circular dependencies."""
        spec = {
            "paths": {
                "/a": {
                    "get": {
                        "parameters": [{"name": "bId", "required": True}],
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "properties": {"aId": {"type": "string"}}
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/b": {
                    "get": {
                        "parameters": [{"name": "aId", "required": True}],
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "properties": {"bId": {"type": "string"}}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "components": {"schemas": {}}
        }
        
        analyzer = DependencyAnalyzer(spec)
        # Should handle circular dependency without infinite loop
        plan = analyzer.get_execution_plan("/a", ["bId"])
        assert "/a" in plan
        assert len(plan) <= 3  # Should not have infinite entries
    
    def test_extract_properties_with_ref(self, spec_with_refs):
        """Test _extract_properties with $ref."""
        analyzer = DependencyAnalyzer(spec_with_refs)
        
        schema = {"$ref": "#/components/schemas/Item"}
        props = analyzer._extract_properties(schema)
        
        assert "itemId" in props
        assert "name" in props
        assert "categoryId" in props
    
    def test_extract_properties_inline(self):
        """Test _extract_properties with inline schema."""
        analyzer = DependencyAnalyzer({"paths": {}, "components": {"schemas": {}}})
        
        schema = {
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"}
            }
        }
        props = analyzer._extract_properties(schema)
        
        assert props == {"id", "name"}
    
    def test_extract_properties_no_properties(self):
        """Test _extract_properties with schema without properties."""
        analyzer = DependencyAnalyzer({"paths": {}, "components": {"schemas": {}}})
        
        schema = {"type": "string"}
        props = analyzer._extract_properties(schema)
        
        assert props == set()
    
    def test_extract_nested_properties(self, spec_with_nested):
        """Test _extract_nested_properties method."""
        analyzer = DependencyAnalyzer(spec_with_nested)
        
        schema = spec_with_nested["paths"]["/complex"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        nested = analyzer._extract_nested_properties(schema)
        
        assert "nestedId" in nested
        assert "arrayItemId" in nested
    
    def test_extract_nested_properties_with_ref(self, spec_with_refs):
        """Test nested properties extraction with $ref."""
        analyzer = DependencyAnalyzer(spec_with_refs)
        
        schema = {"$ref": "#/components/schemas/Item"}
        nested = analyzer._extract_nested_properties(schema)
        
        # metadata is an object, should extract its properties
        assert "tags" in nested or "rating" in nested
    
    def test_is_foreign_key(self):
        """Test _is_foreign_key pattern matching."""
        analyzer = DependencyAnalyzer({"paths": {}, "components": {"schemas": {}}})
        
        # Should match
        assert analyzer._is_foreign_key("userId") is True
        assert analyzer._is_foreign_key("customerId") is True
        assert analyzer._is_foreign_key("orderId") is True
        assert analyzer._is_foreign_key("user_id") is True
        assert analyzer._is_foreign_key("merchantIds") is True
        assert analyzer._is_foreign_key("uuid") is True
        assert analyzer._is_foreign_key("UUID") is True
        assert analyzer._is_foreign_key("id") is True
        assert analyzer._is_foreign_key("ID") is True
        
        # Should not match
        assert analyzer._is_foreign_key("name") is False
        assert analyzer._is_foreign_key("email") is False
        assert analyzer._is_foreign_key("identifier") is False
        assert analyzer._is_foreign_key("") is False
    
    def test_empty_spec(self):
        """Test with empty OpenAPI spec."""
        spec = {"paths": {}, "components": {}}
        analyzer = DependencyAnalyzer(spec)
        
        assert analyzer.param_to_providers == {}
        assert analyzer.dependency_graph == {}
        assert analyzer.find_parameter_providers("any") == []
        assert analyzer.get_execution_plan("/any", []) == ["/any"]
    
    def test_missing_components(self):
        """Test with spec missing components section."""
        spec = {
            "paths": {
                "/test": {
                    "get": {
                        "responses": {}
                    }
                }
            }
        }
        analyzer = DependencyAnalyzer(spec)
        
        assert analyzer.components == {}
        assert analyzer.schemas == {}
    
    def test_multiple_providers_for_parameter(self):
        """Test when multiple endpoints provide the same parameter."""
        spec = {
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "properties": {
                                                "id": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/admins": {
                    "get": {
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "properties": {
                                                "id": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "components": {"schemas": {}}
        }
        
        analyzer = DependencyAnalyzer(spec)
        providers = analyzer.find_parameter_providers("id")
        
        assert len(providers) == 2
        assert "/users" in providers
        assert "/admins" in providers
    
    def test_parameter_in_path_and_response(self):
        """Test parameter that appears in both path params and response."""
        spec = {
            "paths": {
                "/items/{itemId}": {
                    "get": {
                        "parameters": [
                            {"name": "itemId", "required": True}
                        ],
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "properties": {
                                                "itemId": {"type": "string"},
                                                "name": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "components": {"schemas": {}}
        }
        
        analyzer = DependencyAnalyzer(spec)
        
        # itemId should be recognized as both parameter and provider
        assert "itemId" in analyzer.param_to_providers
        assert "/items/{itemId}" in analyzer.param_to_providers["itemId"]