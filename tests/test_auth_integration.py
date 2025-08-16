"""
Integration tests for authentication flow.
Tests the complete auth workflow including token management and credential storage.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from typer.testing import CliRunner
from pathlib import Path
import json
from cli.commands.auth import auth_app, get_token
from cli.state import StateManager
from cli.config import save_credentials, get_saved_credentials
import typer


class TestAuthIntegration:
    """Integration tests for authentication flow."""
    
    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_state_manager(self, tmp_path):
        """Create a mock state manager with temp directory."""
        with patch('cli.commands.auth.state_manager') as mock_sm:
            manager = StateManager()
            manager.state_dir = tmp_path / ".config" / "api-central"
            manager.state_file = manager.state_dir / "state.json"
            manager._ensure_state_dir()
            mock_sm.save_token = manager.save_token
            mock_sm.get_token = manager.get_token
            yield mock_sm
    
    @pytest.fixture
    def mock_api_client_success(self):
        """Mock successful API authentication."""
        with patch('cli.commands.auth.authenticate_client') as mock_auth:
            mock_auth.return_value = "test-bearer-token-123"
            yield mock_auth
    
    @pytest.fixture
    def mock_api_client_failure(self):
        """Mock failed API authentication."""
        with patch('cli.commands.auth.authenticate_client') as mock_auth:
            mock_auth.return_value = None
            yield mock_auth
    
    @pytest.fixture
    def mock_save_credentials(self):
        """Mock credential saving."""
        with patch('cli.commands.auth.save_credentials') as mock_save:
            yield mock_save
    
    @pytest.mark.integration
    @pytest.mark.auth
    def test_successful_authentication(
        self, 
        runner, 
        mock_api_client_success,
        mock_state_manager,
        mock_save_credentials
    ):
        """Test successful authentication flow."""
        # Simulate user input
        result = runner.invoke(
            auth_app, 
            ["get-token"],
            input="test@example.com\npassword123\n"
        )
        
        # Check command succeeded
        assert result.exit_code == 0
        assert "✅ Access Token Updated" in result.stdout
        
        # Verify API was called with correct credentials
        mock_api_client_success.assert_called_once_with(
            "test@example.com", 
            "password123"
        )
        
        # Verify token was saved
        mock_state_manager.save_token.assert_called_once_with(
            "test-bearer-token-123"
        )
        
        # Verify credentials were saved
        mock_save_credentials.assert_called_once_with(
            "test@example.com",
            "password123"
        )
    
    @pytest.mark.integration
    @pytest.mark.auth
    def test_failed_authentication(
        self,
        runner,
        mock_api_client_failure,
        mock_state_manager,
        mock_save_credentials
    ):
        """Test failed authentication flow."""
        # Simulate user input
        result = runner.invoke(
            auth_app,
            ["get-token"],
            input="wrong@example.com\nwrongpassword\n"
        )
        
        # Check command completed (but auth failed)
        assert result.exit_code == 0
        assert "❌ Authentication failed." in result.stdout
        
        # Verify API was called
        mock_api_client_failure.assert_called_once_with(
            "wrong@example.com",
            "wrongpassword"
        )
        
        # Verify token was NOT saved
        mock_state_manager.save_token.assert_not_called()
        
        # Verify credentials were NOT saved
        mock_save_credentials.assert_not_called()
    
    @pytest.mark.integration
    @pytest.mark.auth
    def test_authentication_prompts(self, runner):
        """Test that authentication prompts for email and password."""
        with patch('cli.commands.auth.authenticate_client', return_value=None):
            result = runner.invoke(
                auth_app,
                ["get-token"],
                input="user@test.com\nsecretpass\n"
            )
            
            # Check prompts appear
            assert "Email:" in result.stdout
            assert "Password:" in result.stdout
    
    @pytest.mark.integration
    @pytest.mark.auth
    def test_password_hidden_input(self):
        """Test that password input is hidden."""
        # This tests that typer.prompt is called with hide_input=True
        with patch('cli.commands.auth.typer.prompt') as mock_prompt:
            with patch('cli.commands.auth.authenticate_client'):
                mock_prompt.side_effect = ["test@example.com", "password"]
                
                # Call the function directly
                get_token()
                
                # Check that password prompt has hide_input=True
                calls = mock_prompt.call_args_list
                assert len(calls) == 2
                # First call for email
                assert calls[0][0][0] == "Email"
                assert calls[0][1].get('hide_input', False) is False
                # Second call for password
                assert calls[1][0][0] == "Password"
                assert calls[1][1].get('hide_input', False) is True
    
    @pytest.mark.integration
    @pytest.mark.auth
    def test_authentication_with_special_characters(
        self,
        runner,
        mock_api_client_success,
        mock_state_manager,
        mock_save_credentials
    ):
        """Test authentication with special characters in credentials."""
        # Email with + and password with special chars
        result = runner.invoke(
            auth_app,
            ["get-token"],
            input="user+test@example.com\nP@ssw0rd!#$%\n"
        )
        
        assert result.exit_code == 0
        assert "✅ Access Token Updated" in result.stdout
        
        # Verify special characters were passed correctly
        mock_api_client_success.assert_called_once_with(
            "user+test@example.com",
            "P@ssw0rd!#$%"
        )
    
    @pytest.mark.integration
    @pytest.mark.auth
    def test_authentication_state_persistence(self, tmp_path):
        """Test that authentication state persists correctly."""
        # Create real state manager with temp directory
        state_manager = StateManager()
        state_manager.state_dir = tmp_path / ".config" / "api-central"
        state_manager.state_file = state_manager.state_dir / "state.json"
        state_manager._ensure_state_dir()
        
        with patch('cli.commands.auth.state_manager', state_manager):
            with patch('cli.commands.auth.authenticate_client', return_value="persistent-token"):
                with patch('cli.commands.auth.save_credentials'):
                    runner = CliRunner()
                    result = runner.invoke(
                        auth_app,
                        ["get-token"],
                        input="test@example.com\npassword\n"
                    )
                    
                    assert result.exit_code == 0
        
        # Verify token was persisted to file
        assert state_manager.state_file.exists()
        with open(state_manager.state_file, 'r') as f:
            state = json.load(f)
        
        assert state["access_token"] == "persistent-token"
        assert "token_last_updated" in state
    
    @pytest.mark.integration
    @pytest.mark.auth
    def test_authentication_error_handling(self, runner):
        """Test authentication error handling."""
        # Test network error
        with patch('cli.commands.auth.authenticate_client', side_effect=Exception("Network error")):
            result = runner.invoke(
                auth_app,
                ["get-token"],
                input="test@example.com\npassword\n",
                catch_exceptions=False
            )
            
            # Should raise the exception
            assert "Network error" in str(result.exception)
    
    @pytest.mark.integration
    @pytest.mark.auth
    def test_authentication_empty_credentials(self, runner, mock_api_client_failure):
        """Test authentication with empty credentials."""
        # Empty email and password
        result = runner.invoke(
            auth_app,
            ["get-token"],
            input="\n\n"
        )
        
        # Should handle empty input
        assert result.exit_code == 0
        assert "❌ Authentication failed." in result.stdout
        
        # API should be called with empty strings
        mock_api_client_failure.assert_called_once_with("", "")
    
    @pytest.mark.integration
    @pytest.mark.auth
    def test_authentication_unicode_credentials(
        self,
        runner,
        mock_api_client_success,
        mock_state_manager,
        mock_save_credentials
    ):
        """Test authentication with Unicode characters."""
        # Unicode email and password
        result = runner.invoke(
            auth_app,
            ["get-token"],
            input="user@тест.com\nпароль123\n"
        )
        
        assert result.exit_code == 0
        assert "✅ Access Token Updated" in result.stdout
        
        # Verify Unicode was handled correctly
        mock_api_client_success.assert_called_once_with(
            "user@тест.com",
            "пароль123"
        )
    
    @pytest.mark.integration
    @pytest.mark.auth
    def test_authentication_token_format(
        self,
        runner,
        mock_state_manager,
        mock_save_credentials
    ):
        """Test different token formats are handled correctly."""
        # Test JWT-like token
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        
        with patch('cli.commands.auth.authenticate_client', return_value=jwt_token):
            result = runner.invoke(
                auth_app,
                ["get-token"],
                input="test@example.com\npassword\n"
            )
            
            assert result.exit_code == 0
            assert "✅ Access Token Updated" in result.stdout
            
            # Verify long token was saved correctly
            mock_state_manager.save_token.assert_called_once_with(jwt_token)
    
    @pytest.mark.integration
    @pytest.mark.auth
    def test_authentication_workflow_end_to_end(self, tmp_path):
        """Test complete authentication workflow end-to-end."""
        # Setup real components with temp directory
        state_dir = tmp_path / ".config" / "api-central"
        state_dir.mkdir(parents=True, exist_ok=True)
        
        # Mock the actual API call but use real state management
        with patch('cli.state.StateManager.state_dir', state_dir):
            with patch('cli.state.StateManager.state_file', state_dir / "state.json"):
                with patch('cli.config.get_config_dir', return_value=state_dir):
                    with patch('cli.utils.api_client.requests.post') as mock_post:
                        # Mock successful API response
                        mock_response = Mock()
                        mock_response.status_code = 200
                        mock_response.json.return_value = {
                            "access_token": "end-to-end-token",
                            "token_type": "Bearer",
                            "expires_in": 3600
                        }
                        mock_post.return_value = mock_response
                        
                        # Run authentication
                        runner = CliRunner()
                        result = runner.invoke(
                            auth_app,
                            ["get-token"],
                            input="e2e@test.com\ne2epassword\n"
                        )
                        
                        # Verify success
                        assert result.exit_code == 0
                        assert "✅ Access Token Updated" in result.stdout
                        
                        # Verify state file was created
                        state_file = state_dir / "state.json"
                        assert state_file.exists()
                        
                        # Verify token was saved
                        with open(state_file, 'r') as f:
                            state = json.load(f)
                        assert "access_token" in state
                        # Note: actual token might be processed/extracted
                        assert state.get("access_token") is not None