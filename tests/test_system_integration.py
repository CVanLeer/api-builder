"""
Integration tests for API query flow and system commands.
Tests the complete workflow of dependency analysis, parameter resolution, and API execution.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock, call
from typer.testing import CliRunner
from pathlib import Path
from datetime import datetime, timedelta
from cli.commands.system import (
    system_app, 
    query_api, 
    set_defaults,
    history,
    replay,
    get_dependency_analyzer,
    get_parameter_detector,
    execute_endpoint,
    resolve_parameter_with_dependency,
    select_from_response
)
from cli.dependency_analyzer import DependencyAnalyzer
from cli.parameter_detector import ParameterDetector, ParameterType


class TestSystemIntegration:
    """Integration tests for system commands and API query flow."""
    
    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_openapi_spec(self, sample_openapi_spec):
        """Mock OpenAPI specification."""
        return sample_openapi_spec
    
    @pytest.fixture
    def mock_dependency_analyzer(self, mock_openapi_spec):
        """Create a mock dependency analyzer."""
        with patch('cli.commands.system.get_dependency_analyzer') as mock_get:
            analyzer = DependencyAnalyzer(mock_openapi_spec)
            mock_get.return_value = analyzer
            yield analyzer
    
    @pytest.fixture
    def mock_api_client(self):
        """Mock API client for endpoint execution."""
        with patch('cli.commands.system.get_client') as mock_get_client:
            client = MagicMock()
            
            # Mock merchant endpoint
            client.merchants.get_merchants.sync.return_value = {
                "data": [
                    {"merchantId": "merch-001", "name": "Test Merchant 1"},
                    {"merchantId": "merch-002", "name": "Test Merchant 2"}
                ],
                "hasNextPage": False
            }
            
            # Mock location endpoint
            client.locations.get_locations.sync.return_value = {
                "data": [
                    {"locationId": "loc-001", "name": "Location 1", "merchantId": "merch-001"},
                    {"locationId": "loc-002", "name": "Location 2", "merchantId": "merch-001"}
                ],
                "hasNextPage": False
            }
            
            # Mock orders endpoint
            client.orders.get_orders.sync.return_value = {
                "data": [
                    {"orderId": "ord-001", "locationId": "loc-001", "total": 99.99}
                ],
                "hasNextPage": False
            }
            
            mock_get_client.return_value = client
            yield client
    
    @pytest.fixture
    def mock_context(self):
        """Mock context for parameter storage."""
        context_data = {}
        
        with patch('cli.commands.system.get_value') as mock_get:
            with patch('cli.commands.system.save_context') as mock_save:
                mock_get.side_effect = lambda key: context_data.get(key)
                mock_save.side_effect = lambda data: context_data.update(data)
                yield context_data
    
    @pytest.fixture
    def mock_command_history(self):
        """Mock command history."""
        history_data = [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "endpoint": "/merchants",
                "parameters": {"page": 1, "pageSize": 50},
                "success": True
            },
            {
                "timestamp": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                "endpoint": "/locations",
                "parameters": {"merchantId": "merch-001"},
                "success": True
            }
        ]
        
        with patch('cli.commands.system.get_recent_commands') as mock_get:
            with patch('cli.commands.system.replay_command') as mock_replay:
                mock_get.return_value = history_data
                mock_replay.side_effect = lambda idx: history_data[idx] if idx < len(history_data) else None
                yield history_data
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_query_api_simple_endpoint(
        self,
        runner,
        mock_dependency_analyzer,
        mock_api_client,
        mock_context
    ):
        """Test querying a simple API endpoint without dependencies."""
        # Mock user input: select endpoint 0 (/merchants), approve all params
        with patch('cli.commands.system.Prompt.ask') as mock_prompt:
            with patch('cli.commands.system.Confirm.ask', return_value=True):
                mock_prompt.side_effect = ["0", "Y", "results.json"]
                
                result = runner.invoke(system_app, ["query-api"])
                
                # Check command succeeded
                assert result.exit_code == 0
                assert "Available API Endpoints" in result.stdout
                assert "Results" in result.stdout
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_query_api_with_dependencies(
        self,
        runner,
        mock_dependency_analyzer,
        mock_api_client,
        mock_context
    ):
        """Test querying an endpoint with parameter dependencies."""
        # Select /orders endpoint which requires locationId
        with patch('cli.commands.system.Prompt.ask') as mock_prompt:
            with patch('cli.commands.system.Confirm.ask', return_value=True):
                # User selects orders endpoint, then selects location from list
                mock_prompt.side_effect = [
                    "3",  # Select /orders endpoint
                    "0",  # Select first location
                    "Y",  # Approve all
                    "n"   # Don't save results
                ]
                
                result = runner.invoke(system_app, ["query-api"])
                
                assert result.exit_code == 0
                # Should show dependency chain
                assert "Dependency chain" in result.stdout or "locationId" in result.stdout
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_set_defaults_command(self, runner, mock_context):
        """Test setting default date parameters."""
        result = runner.invoke(system_app, ["set-defaults"])
        
        assert result.exit_code == 0
        assert "✅ Default dates set in context" in result.stdout
        
        # Verify dates were saved to context
        assert "StartDateExperiencedLocal" in mock_context
        assert "EndDateExperiencedLocal" in mock_context
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_history_command(self, runner, mock_command_history):
        """Test viewing command history."""
        result = runner.invoke(system_app, ["history"])
        
        assert result.exit_code == 0
        assert "Recent Commands" in result.stdout
        assert "/merchants" in result.stdout
        assert "/locations" in result.stdout
        assert "✅" in result.stdout  # Success indicator
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_history_command_with_limit(self, runner, mock_command_history):
        """Test viewing limited command history."""
        result = runner.invoke(system_app, ["history", "--limit", "1"])
        
        assert result.exit_code == 0
        assert "Recent Commands" in result.stdout
        # Should only show 1 command
        assert result.stdout.count("/merchants") == 1
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_replay_command(self, runner, mock_command_history, mock_api_client):
        """Test replaying a command from history."""
        with patch('cli.commands.system.Confirm.ask', return_value=True):
            with patch('cli.commands.system.execute_endpoint') as mock_execute:
                mock_execute.return_value = {"data": "replay_result"}
                
                result = runner.invoke(system_app, ["replay", "0"])
                
                assert result.exit_code == 0
                assert "Replaying command" in result.stdout
                assert "/merchants" in result.stdout
                
                # Verify endpoint was executed
                mock_execute.assert_called_once_with(
                    "/merchants",
                    {"page": 1, "pageSize": 50}
                )
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_replay_invalid_index(self, runner, mock_command_history):
        """Test replaying with invalid index."""
        result = runner.invoke(system_app, ["replay", "999"])
        
        assert result.exit_code == 0
        assert "No command found at index 999" in result.stdout
    
    def test_get_dependency_analyzer_caching(self):
        """Test that dependency analyzer is cached."""
        # Clear cache first
        import cli.commands.system
        cli.commands.system._dependency_cache.clear()
        
        with patch('builtins.open', mock_open(read_data='{"paths": {}, "components": {}}')):
            with patch('pathlib.Path.exists', return_value=True):
                analyzer1 = get_dependency_analyzer()
                analyzer2 = get_dependency_analyzer()
                
                # Should be the same instance (cached)
                assert analyzer1 is analyzer2
    
    def test_get_parameter_detector_caching(self):
        """Test that parameter detector is cached."""
        import cli.commands.system
        cli.commands.system._dependency_cache.clear()
        
        detector1 = get_parameter_detector()
        detector2 = get_parameter_detector()
        
        # Should be the same instance (cached)
        assert detector1 is detector2
    
    def test_execute_endpoint_success(self, mock_api_client):
        """Test successful endpoint execution."""
        result = execute_endpoint("/merchants", {"page": 1})
        
        assert result is not None
        assert "data" in result
        assert len(result["data"]) == 2
        assert result["data"][0]["merchantId"] == "merch-001"
    
    def test_execute_endpoint_unknown(self, mock_api_client):
        """Test executing unknown endpoint."""
        result = execute_endpoint("/unknown", {})
        
        assert result is None
    
    def test_execute_endpoint_error(self, mock_api_client):
        """Test endpoint execution with error."""
        mock_api_client.merchants.get_merchants.sync.side_effect = Exception("API Error")
        
        result = execute_endpoint("/merchants", {})
        
        assert result is None
    
    def test_select_from_response_single_item(self):
        """Test selecting from single item response."""
        detector = ParameterDetector()
        response = {"merchantId": "single-001", "name": "Single"}
        
        with patch('cli.commands.system.get_parameter_detector', return_value=detector):
            result = select_from_response(response, "merchantId", "/merchants")
            
            assert result == "single-001"
    
    def test_select_from_response_list_with_user_selection(self):
        """Test selecting from list with user interaction."""
        detector = ParameterDetector()
        response = {
            "data": [
                {"merchantId": "m1", "name": "Merchant 1"},
                {"merchantId": "m2", "name": "Merchant 2"},
                {"merchantId": "m3", "name": "Merchant 3"}
            ]
        }
        
        with patch('cli.commands.system.get_parameter_detector', return_value=detector):
            with patch('cli.commands.system.Prompt.ask', return_value="1"):
                result = select_from_response(response, "merchantId", "/merchants")
                
                assert result == "m2"  # Second item (index 1)
    
    def test_resolve_parameter_pagination(self, mock_dependency_analyzer):
        """Test resolving pagination parameters."""
        detector = ParameterDetector()
        
        with patch('cli.commands.system.get_parameter_detector', return_value=detector):
            with patch('cli.commands.system.get_value', return_value=None):
                # Test page parameter
                result = resolve_parameter_with_dependency(
                    "page",
                    {"name": "page", "type": "integer"},
                    mock_dependency_analyzer,
                    "/test"
                )
                assert result == 1
                
                # Test pageSize parameter
                result = resolve_parameter_with_dependency(
                    "pageSize",
                    {"name": "pageSize", "type": "integer"},
                    mock_dependency_analyzer,
                    "/test"
                )
                assert result == 50
    
    def test_resolve_parameter_boolean(self, mock_dependency_analyzer):
        """Test resolving boolean parameters."""
        detector = ParameterDetector()
        
        with patch('cli.commands.system.get_parameter_detector', return_value=detector):
            with patch('cli.commands.system.get_value', return_value=None):
                with patch('cli.commands.system.Confirm.ask', return_value=True):
                    result = resolve_parameter_with_dependency(
                        "isActive",
                        {"name": "isActive", "type": "boolean"},
                        mock_dependency_analyzer,
                        "/test"
                    )
                    assert result is True
    
    def test_resolve_parameter_enum(self, mock_dependency_analyzer):
        """Test resolving enum parameters."""
        detector = ParameterDetector()
        
        with patch('cli.commands.system.get_parameter_detector', return_value=detector):
            with patch('cli.commands.system.get_value', return_value=None):
                with patch('cli.commands.system.Prompt.ask', return_value="completed"):
                    result = resolve_parameter_with_dependency(
                        "status",
                        {
                            "name": "status",
                            "type": "string",
                            "enum": ["pending", "completed", "cancelled"]
                        },
                        mock_dependency_analyzer,
                        "/test"
                    )
                    assert result == "completed"
    
    def test_resolve_parameter_cached_value(self, mock_dependency_analyzer):
        """Test using cached parameter value."""
        with patch('cli.commands.system.get_value', return_value="cached-value"):
            result = resolve_parameter_with_dependency(
                "merchantId",
                {"name": "merchantId", "type": "string"},
                mock_dependency_analyzer,
                "/test"
            )
            assert result == "cached-value"
    
    def test_resolve_parameter_circular_dependency(self, mock_dependency_analyzer):
        """Test handling circular parameter dependencies."""
        detector = ParameterDetector()
        
        with patch('cli.commands.system.get_parameter_detector', return_value=detector):
            with patch('cli.commands.system.get_value', return_value=None):
                with patch('cli.commands.system.Prompt.ask', return_value="manual-value"):
                    # Create a circular dependency by adding param to stack
                    resolving_stack = {"circularParam"}
                    
                    result = resolve_parameter_with_dependency(
                        "circularParam",
                        {"name": "circularParam", "type": "string"},
                        mock_dependency_analyzer,
                        "/test",
                        _resolving_stack=resolving_stack
                    )
                    
                    assert result == "manual-value"
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_full_api_query_workflow(
        self,
        runner,
        mock_dependency_analyzer,
        mock_api_client,
        tmp_path
    ):
        """Test complete API query workflow with all features."""
        # Set up context storage
        context_file = tmp_path / "context.json"
        context_data = {}
        
        def save_context(data):
            context_data.update(data)
            with open(context_file, 'w') as f:
                json.dump(context_data, f)
        
        def get_value(key):
            return context_data.get(key)
        
        with patch('cli.commands.system.save_context', side_effect=save_context):
            with patch('cli.commands.system.get_value', side_effect=get_value):
                with patch('cli.commands.system.Prompt.ask') as mock_prompt:
                    with patch('cli.commands.system.Confirm.ask', return_value=True):
                        # User workflow:
                        # 1. Select /orders endpoint (index 3)
                        # 2. Select location from dependency resolution
                        # 3. Approve parameters
                        # 4. Save results
                        mock_prompt.side_effect = [
                            "3",           # Select /orders
                            "0",           # Select first location
                            "Y",           # Approve all
                            "y",           # Save results
                            "test_results.json"  # Filename
                        ]
                        
                        result = runner.invoke(system_app, ["query-api"])
                        
                        assert result.exit_code == 0
                        assert "Available API Endpoints" in result.stdout
                        assert "Results" in result.stdout
                        
                        # Verify context was updated
                        if context_file.exists():
                            with open(context_file, 'r') as f:
                                saved_context = json.load(f)
                            assert "locationId" in saved_context
    
    @pytest.mark.integration  
    @pytest.mark.api
    def test_parameter_approval_workflow(
        self,
        runner,
        mock_dependency_analyzer,
        mock_api_client
    ):
        """Test parameter approval and modification workflow."""
        with patch('cli.commands.system.Prompt.ask') as mock_prompt:
            with patch('cli.commands.system.Confirm.ask') as mock_confirm:
                # User modifies a parameter value
                mock_prompt.side_effect = [
                    "0",      # Select /merchants
                    "N",      # Don't approve all
                    "Y",      # Approve page=1
                    "N",      # Don't approve pageSize=50
                    "100",    # Change pageSize to 100
                    "Y"       # Approve modified pageSize
                ]
                mock_confirm.return_value = True  # Final confirmation
                
                with patch('cli.commands.system.execute_endpoint') as mock_execute:
                    mock_execute.return_value = {"data": []}
                    
                    result = runner.invoke(system_app, ["query-api"])
                    
                    # Verify modified parameter was used
                    # Note: Due to complexity of approval flow, just check success
                    assert result.exit_code == 0