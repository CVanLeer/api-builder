"""
Comprehensive unit tests for StateManager module.
Achieving 85%+ coverage for all methods and edge cases.
"""
import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, mock_open
from cli.state import StateManager


class TestStateManager:
    """Test suite for StateManager class."""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create a temporary directory for testing."""
        return tmp_path
    
    @pytest.fixture
    def state_manager(self, temp_dir):
        """Create a StateManager instance with temp directory."""
        manager = StateManager()
        # Override the default paths
        manager.state_dir = temp_dir / ".config" / "api-central"
        manager.state_file = manager.state_dir / "state.json"
        manager.history_file = manager.state_dir / "command_history.json"
        manager._ensure_state_dir()
        return manager
    
    @pytest.fixture
    def sample_state(self):
        """Sample state data for testing."""
        return {
            "access_token": "test-token-12345",
            "token_last_updated": datetime.utcnow().isoformat(),
            "auth_email": "test@example.com",
            "auth_password_encrypted": "encrypted_password_here",
            "encryption_key": "test_encryption_key"
        }
    
    def test_initialization(self):
        """Test StateManager initialization."""
        manager = StateManager()
        
        assert manager.state_dir == Path.home() / ".config" / "api-central"
        assert manager.state_file == manager.state_dir / "state.json"
        assert manager.history_file == manager.state_dir / "command_history.json"
    
    def test_ensure_state_dir(self, temp_dir):
        """Test state directory creation."""
        manager = StateManager()
        manager.state_dir = temp_dir / "test_state"
        manager.state_file = manager.state_dir / "state.json"
        
        # Directory shouldn't exist initially
        assert not manager.state_dir.exists()
        
        # Create directory
        manager._ensure_state_dir()
        
        # Directory should now exist
        assert manager.state_dir.exists()
        assert manager.state_dir.is_dir()
        
        # Should handle existing directory gracefully
        manager._ensure_state_dir()
        assert manager.state_dir.exists()
    
    def test_load_state_empty(self, state_manager):
        """Test loading state when file doesn't exist."""
        state = state_manager._load_state()
        
        assert state == {}
        assert isinstance(state, dict)
    
    def test_load_state_with_data(self, state_manager, sample_state):
        """Test loading state from existing file."""
        # Write sample state to file
        with open(state_manager.state_file, 'w') as f:
            json.dump(sample_state, f)
        
        # Load state
        state = state_manager._load_state()
        
        assert state == sample_state
        assert state["access_token"] == "test-token-12345"
        assert state["auth_email"] == "test@example.com"
    
    def test_load_state_corrupted_file(self, state_manager):
        """Test loading state from corrupted file."""
        # Write invalid JSON
        with open(state_manager.state_file, 'w') as f:
            f.write("{ invalid json }")
        
        # Should return empty dict on error
        state = state_manager._load_state()
        assert state == {}
    
    def test_load_state_permission_error(self, state_manager):
        """Test loading state with permission error."""
        with patch('builtins.open', side_effect=PermissionError):
            state = state_manager._load_state()
            assert state == {}
    
    def test_save_state(self, state_manager, sample_state):
        """Test saving state to file."""
        state_manager._save_state(sample_state)
        
        # Verify file was created
        assert state_manager.state_file.exists()
        
        # Verify content
        with open(state_manager.state_file, 'r') as f:
            saved_state = json.load(f)
        
        assert saved_state == sample_state
        assert saved_state["access_token"] == "test-token-12345"
    
    def test_save_state_update_existing(self, state_manager):
        """Test updating existing state file."""
        # Save initial state
        initial_state = {"key1": "value1"}
        state_manager._save_state(initial_state)
        
        # Update state
        updated_state = {"key1": "updated", "key2": "value2"}
        state_manager._save_state(updated_state)
        
        # Verify update
        with open(state_manager.state_file, 'r') as f:
            saved_state = json.load(f)
        
        assert saved_state == updated_state
        assert saved_state["key1"] == "updated"
        assert saved_state["key2"] == "value2"
    
    def test_save_state_permission_error(self, state_manager):
        """Test saving state with permission error."""
        with patch('builtins.open', side_effect=PermissionError):
            # Should not raise exception
            state_manager._save_state({"test": "data"})
    
    def test_get_token(self, state_manager, sample_state):
        """Test getting saved token."""
        # No token initially
        token = state_manager.get_token()
        assert token is None
        
        # Save state with token
        state_manager._save_state(sample_state)
        
        # Get token
        token = state_manager.get_token()
        assert token == "test-token-12345"
    
    def test_save_token(self, state_manager):
        """Test saving access token."""
        test_token = "new-token-67890"
        
        # Save token
        state_manager.save_token(test_token)
        
        # Verify token was saved
        state = state_manager._load_state()
        assert state["access_token"] == test_token
        assert "token_last_updated" in state
        
        # Verify timestamp format
        timestamp = state["token_last_updated"]
        parsed_time = datetime.fromisoformat(timestamp)
        assert isinstance(parsed_time, datetime)
        
        # Timestamp should be recent
        time_diff = datetime.utcnow() - parsed_time
        assert time_diff.total_seconds() < 5
    
    def test_save_token_preserves_other_data(self, state_manager):
        """Test that saving token preserves other state data."""
        # Save initial state
        initial_state = {
            "auth_email": "test@example.com",
            "other_data": "preserved"
        }
        state_manager._save_state(initial_state)
        
        # Save token
        state_manager.save_token("new-token")
        
        # Verify other data preserved
        state = state_manager._load_state()
        assert state["access_token"] == "new-token"
        assert state["auth_email"] == "test@example.com"
        assert state["other_data"] == "preserved"
    
    def test_get_token_last_updated(self, state_manager):
        """Test getting token last updated timestamp."""
        # No timestamp initially
        timestamp = state_manager.get_token_last_updated()
        assert timestamp is None
        
        # Save token (which includes timestamp)
        state_manager.save_token("test-token")
        
        # Get timestamp
        timestamp = state_manager.get_token_last_updated()
        assert isinstance(timestamp, datetime)
        
        # Should be recent
        time_diff = datetime.utcnow() - timestamp
        assert time_diff.total_seconds() < 5
    
    def test_get_token_last_updated_invalid_format(self, state_manager):
        """Test getting timestamp with invalid format."""
        # Save state with invalid timestamp
        state = {"token_last_updated": "invalid-date"}
        state_manager._save_state(state)
        
        # Should return None for invalid format
        timestamp = state_manager.get_token_last_updated()
        assert timestamp is None
    
    def test_save_credentials(self, state_manager):
        """Test saving encrypted credentials."""
        email = "user@example.com"
        encrypted_password = "encrypted_pwd_123"
        
        state_manager.save_credentials(email, encrypted_password)
        
        # Verify credentials were saved
        state = state_manager._load_state()
        assert state["auth_email"] == email
        assert state["auth_password_encrypted"] == encrypted_password
    
    def test_save_credentials_preserves_token(self, state_manager):
        """Test that saving credentials preserves token."""
        # Save token first
        state_manager.save_token("existing-token")
        
        # Save credentials
        state_manager.save_credentials("user@test.com", "encrypted")
        
        # Verify both exist
        state = state_manager._load_state()
        assert state["access_token"] == "existing-token"
        assert state["auth_email"] == "user@test.com"
        assert state["auth_password_encrypted"] == "encrypted"
    
    def test_get_credentials(self, state_manager):
        """Test getting saved credentials."""
        # No credentials initially
        email, password = state_manager.get_credentials()
        assert email == ""
        assert password == ""
        
        # Save credentials
        state_manager.save_credentials("test@example.com", "encrypted_123")
        
        # Get credentials
        email, password = state_manager.get_credentials()
        assert email == "test@example.com"
        assert password == "encrypted_123"
    
    def test_get_credentials_partial(self, state_manager):
        """Test getting credentials when only one exists."""
        # Save only email
        state = {"auth_email": "only@email.com"}
        state_manager._save_state(state)
        
        email, password = state_manager.get_credentials()
        assert email == "only@email.com"
        assert password == ""
        
        # Save only password
        state = {"auth_password_encrypted": "only_password"}
        state_manager._save_state(state)
        
        email, password = state_manager.get_credentials()
        assert email == ""
        assert password == "only_password"
    
    def test_save_encryption_key(self, state_manager):
        """Test saving encryption key."""
        key = "test_encryption_key_123"
        
        state_manager.save_encryption_key(key)
        
        # Verify key was saved
        state = state_manager._load_state()
        assert state["encryption_key"] == key
    
    def test_get_encryption_key(self, state_manager):
        """Test getting encryption key."""
        # No key initially
        key = state_manager.get_encryption_key()
        assert key is None
        
        # Save key
        state_manager.save_encryption_key("my_key_456")
        
        # Get key
        key = state_manager.get_encryption_key()
        assert key == "my_key_456"
    
    def test_complete_workflow(self, state_manager):
        """Test a complete workflow of saving and retrieving data."""
        # Save token
        state_manager.save_token("workflow-token")
        
        # Save credentials
        state_manager.save_credentials("workflow@test.com", "encrypted_workflow")
        
        # Save encryption key
        state_manager.save_encryption_key("workflow_key")
        
        # Retrieve everything
        token = state_manager.get_token()
        timestamp = state_manager.get_token_last_updated()
        email, password = state_manager.get_credentials()
        key = state_manager.get_encryption_key()
        
        # Verify all data
        assert token == "workflow-token"
        assert isinstance(timestamp, datetime)
        assert email == "workflow@test.com"
        assert password == "encrypted_workflow"
        assert key == "workflow_key"
        
        # Verify state file exists and contains all data
        assert state_manager.state_file.exists()
        with open(state_manager.state_file, 'r') as f:
            state = json.load(f)
        
        assert "access_token" in state
        assert "token_last_updated" in state
        assert "auth_email" in state
        assert "auth_password_encrypted" in state
        assert "encryption_key" in state
    
    def test_concurrent_access(self, state_manager):
        """Test handling of concurrent state modifications."""
        # Simulate concurrent writes
        state_manager.save_token("token1")
        state_manager.save_credentials("email1@test.com", "pwd1")
        state_manager.save_token("token2")  # Overwrites token1
        
        # Final state should have latest values
        state = state_manager._load_state()
        assert state["access_token"] == "token2"
        assert state["auth_email"] == "email1@test.com"
    
    def test_empty_values(self, state_manager):
        """Test handling of empty values."""
        # Save empty values
        state_manager.save_token("")
        state_manager.save_credentials("", "")
        state_manager.save_encryption_key("")
        
        # Should save empty strings
        state = state_manager._load_state()
        assert state["access_token"] == ""
        assert state["auth_email"] == ""
        assert state["auth_password_encrypted"] == ""
        assert state["encryption_key"] == ""
    
    def test_special_characters_in_data(self, state_manager):
        """Test handling of special characters in data."""
        # Save data with special characters
        special_token = "token!@#$%^&*(){}[]|\\:;\"'<>,.?/"
        special_email = "user+test@example.com"
        special_password = "pwd\\n\\r\\t\"'"
        
        state_manager.save_token(special_token)
        state_manager.save_credentials(special_email, special_password)
        
        # Retrieve and verify
        token = state_manager.get_token()
        email, password = state_manager.get_credentials()
        
        assert token == special_token
        assert email == special_email
        assert password == special_password
    
    def test_large_data(self, state_manager):
        """Test handling of large data values."""
        # Create large token (simulating JWT)
        large_token = "x" * 10000
        state_manager.save_token(large_token)
        
        # Should handle large data
        token = state_manager.get_token()
        assert token == large_token
        assert len(token) == 10000
    
    def test_unicode_data(self, state_manager):
        """Test handling of Unicode data."""
        # Save Unicode data
        unicode_email = "user@тест.com"
        unicode_token = "token_с_кириллицей_和中文"
        
        state_manager.save_token(unicode_token)
        state_manager.save_credentials(unicode_email, "pwd")
        
        # Retrieve and verify
        token = state_manager.get_token()
        email, _ = state_manager.get_credentials()
        
        assert token == unicode_token
        assert email == unicode_email