"""
Centralized state management for API Central.
Handles tokens, encryption keys, and command history.
"""
from pathlib import Path
from typing import Optional, Dict, Any
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class StateManager:
    """Manages application state in user directory."""

    def __init__(self):
        self.state_dir = Path.home() / ".config" / "api-central"
        self.state_file = self.state_dir / "state.json"
        self.history_file = self.state_dir / "command_history.json"
        self._ensure_state_dir()

    def _ensure_state_dir(self):
        """Create state directory if it doesn't exist."""
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> Dict[str, Any]:
        """Load state from file."""
        if not self.state_file.exists():
            return {}
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return {}

    def _save_state(self, state: Dict[str, Any]):
        """Save state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def get_token(self) -> Optional[str]:
        """Get saved access token."""
        state = self._load_state()
        return state.get('access_token')

    def save_token(self, token: str):
        """Save access token with timestamp."""
        state = self._load_state()
        state.update({
            'access_token': token,
            'token_last_updated': datetime.utcnow().isoformat()
        })
        self._save_state(state)

    def get_token_last_updated(self) -> Optional[datetime]:
        """Get token last updated timestamp."""
        state = self._load_state()
        timestamp = state.get('token_last_updated')
        if timestamp:
            try:
                return datetime.fromisoformat(timestamp)
            except Exception:
                return None
        return None

    def save_credentials(self, email: str, encrypted_password: str):
        """Save encrypted credentials."""
        state = self._load_state()
        state.update({
            'auth_email': email,
            'auth_password_encrypted': encrypted_password
        })
        self._save_state(state)

    def get_credentials(self) -> tuple[str, str]:
        """Get saved email and encrypted password."""
        state = self._load_state()
        email = state.get('auth_email', '')
        encrypted_password = state.get('auth_password_encrypted', '')
        return email, encrypted_password

    def save_encryption_key(self, key: str):
        """Save encryption key."""
        state = self._load_state()
        state['encryption_key'] = key
        self._save_state(state)

    def get_encryption_key(self) -> Optional[str]:
        """Get encryption key."""
        state = self._load_state()
        return state.get('encryption_key')


# Global state manager instance
state_manager = StateManager() 