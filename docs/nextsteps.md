# Next Steps: API Central Refactoring Plan

## Overview

This document outlines the comprehensive refactoring plan for the API Central project. Phase 1 has been completed, and this document provides detailed instructions for implementing Phases 2 and 3.

## Phase 1: Completed ✅

### What Was Accomplished

#### 1. Removed Architectural Redundancy
- **Deleted** `scripts/generate_endpoints.py` - redundant code generator
- **Deleted** `cli/endpoints/` directory - all generated endpoint functions
- **Problem Solved**: Eliminated dual code generation strategy that created maintenance overhead

#### 2. Unified OpenAPI Specifications
- **Verified** `openapi/openai.json` (228KB) as the real API specification (Tattle Partners API)
- **Removed** `openapi/example_api.yaml` (empty placeholder file)
- **Updated** `scripts/regen_client.py` to point to correct OpenAPI spec
- **Problem Solved**: Single source of truth for API definitions

#### 3. Fixed Configuration Issues
- **Updated** `cli/config.py` Settings class to ignore extra fields in `.env` file
- **Generated** proper API client from real OpenAPI specification
- **Problem Solved**: Configuration validation errors preventing application startup

#### 4. Verified Project Stability
- **Fixed** test suite - all tests passing
- **Confirmed** basic CLI functionality works
- **Note**: `system query-api` command currently broken (expected - will be fixed in Phase 2-3)

### Technical Changes Made

```bash
# Files deleted:
scripts/generate_endpoints.py
cli/endpoints/ (entire directory)
openapi/example_api.yaml

# Files modified:
scripts/regen_client.py - updated to use openai.json
cli/config.py - added extra="ignore" to Settings class

# Generated:
api_client/ - new properly generated client from openai.json
```

## Phase 2: Centralize State and Configuration 🔄

### Objective
Move application state (tokens, keys, history) out of `.env` files into proper application directories and implement robust state management.

### Current Problems
- **Improper State Management**: Application modifies `.env` file to store dynamic state
- **Security Risk**: Tokens and credentials mixed with configuration
- **Multi-user Issues**: `.env` modification doesn't work in containerized/multi-user environments

### Implementation Steps

#### 2.1 Create State Management Module

**Create** `cli/state.py`:

```python
"""
Centralized state management for API Central.
Handles tokens, encryption keys, and command history.
"""
from pathlib import Path
from typing import Optional, Dict, Any
import json
import os
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
```

#### 2.2 Refactor cli/config.py

**Modify** `cli/config.py` to use state manager:

```python
# Remove these functions (they write to .env):
# - update_env_file()
# - save_token()
# - save_credentials()
# - get_token_last_updated() (move logic to state.py)

# Update these functions to use state_manager:
def get_saved_token() -> str:
    """Retrieve the saved access token."""
    from cli.state import state_manager
    return state_manager.get_token() or ""

def save_token(token: str):
    """Save the access token and update timestamp."""
    from cli.state import state_manager
    state_manager.save_token(token)

def get_token_last_updated() -> Optional[datetime]:
    """Get the last updated timestamp for the token."""
    from cli.state import state_manager
    return state_manager.get_token_last_updated()

def save_credentials(email: str, password: str):
    """Save email and encrypted password."""
    from cli.state import state_manager
    encrypted_password = encrypt_password(password)
    state_manager.save_credentials(email, encrypted_password)

def get_saved_credentials() -> tuple[str, str]:
    """Get saved email and decrypted password."""
    from cli.state import state_manager
    email, encrypted_password = state_manager.get_credentials()
    if not email or not encrypted_password:
        return "", ""
    try:
        password = decrypt_password(encrypted_password)
        return email, password
    except Exception as e:
        logger.error(f"Failed to decrypt stored password: {e}")
        return "", ""

def get_or_create_encryption_key() -> bytes:
    """Get or create an encryption key for storing credentials."""
    from cli.state import state_manager
    key_str = state_manager.get_encryption_key()
    if key_str:
        return base64.urlsafe_b64decode(key_str)
    
    # Generate new key
    key = Fernet.generate_key()
    key_str = base64.urlsafe_b64encode(key).decode()
    state_manager.save_encryption_key(key_str)
    return key
```

#### 2.3 Update cli/commands/auth.py

**Modify** authentication commands to use new state management:

- Update `get-token` command to use `state_manager.save_token()`
- Ensure all credential storage goes through state manager
- Test that authentication flow works with new state system

#### 2.4 Testing Phase 2

```bash
# Test token storage
poetry run python -m cli.main auth get-token

# Verify state directory creation
ls -la ~/.config/api-central/

# Verify .env file is no longer modified for dynamic state
```

## Phase 3: Integrate the API Client 🔄

### Objective
Unify all API interactions to use the generated `api_client/` SDK instead of direct `requests` calls.

### Current Problems
- **Scattered API Logic**: Direct `requests` calls throughout codebase
- **No Type Safety**: Manual request building prone to errors
- **Duplicated Auth Logic**: Authorization headers repeated everywhere
- **Broken System Commands**: `system.py` relies on deleted `cli/endpoints/`

### Implementation Steps

#### 3.1 Create API Client Factory

**Create** `cli/utils/api_client.py`:

```python
"""
Centralized API client factory and utilities.
"""
from typing import Optional
import logging
from api_client import Client
from api_client.api.authentication import post_auth_token
from api_client.models import AuthenticationRequest
from cli.config import settings
from cli.state import state_manager

logger = logging.getLogger(__name__)

def get_client() -> Client:
    """
    Get configured API client with authentication.
    This is the single entry point for all API operations.
    """
    token = state_manager.get_token()
    
    # Configure client with base URL and token
    client = Client(
        base_url=settings.api_base_url,
        headers={"Authorization": f"Bearer {token}"} if token else {}
    )
    
    return client

def authenticate_client(email: str, password: str) -> Optional[str]:
    """
    Authenticate and return access token using the API client.
    """
    client = Client(base_url=settings.api_base_url)
    
    auth_request = AuthenticationRequest(
        email=email,
        password=password
    )
    
    try:
        response = post_auth_token.sync(client=client, json_body=auth_request)
        if response and hasattr(response, 'access_token'):
            return response.access_token
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
    
    return None

def refresh_token_if_needed() -> bool:
    """
    Automatically refresh token if expired.
    Returns True if token is valid/refreshed, False if manual auth needed.
    """
    from datetime import datetime, timedelta
    
    last_updated = state_manager.get_token_last_updated()
    if not last_updated or (datetime.utcnow() - last_updated > timedelta(hours=23)):
        # Try to auto-refresh using saved credentials
        from cli.config import get_saved_credentials
        email, password = get_saved_credentials()
        if email and password:
            token = authenticate_client(email, password)
            if token:
                state_manager.save_token(token)
                return True
        return False
    return True
```

#### 3.2 Refactor cli/commands/auth.py

**Replace** direct `requests` calls with API client:

```python
# Replace this pattern:
# response = requests.post(url, json=payload)

# With this pattern:
from cli.utils.api_client import authenticate_client

@auth_app.command()
def get_token(email: str, password: str):
    """Get access token using email and password."""
    token = authenticate_client(email, password)
    if token:
        state_manager.save_token(token)
        console.print("[green]✅ Token saved successfully[/green]")
    else:
        console.print("[red]❌ Authentication failed[/red]")
```

#### 3.3 Completely Refactor cli/commands/system.py

This file needs a major overhaul since it depends on the deleted `cli/endpoints/`:

**Replace** `execute_endpoint()` function:

```python
def execute_endpoint(endpoint: str, params: dict) -> dict | None:
    """Execute an endpoint using the API client."""
    try:
        client = get_client()
        
        # Map endpoint paths to API client methods
        # This requires analyzing the generated api_client structure
        # and creating a mapping from OpenAPI paths to client methods
        
        # Example mapping (needs to be completed based on generated client):
        endpoint_mapping = {
            "/merchants": lambda: client.merchants.get_merchants.sync(**params),
            "/locations": lambda: client.locations.get_locations.sync(**params),
            "/groups": lambda: client.groups.get_groups.sync(**params),
            # ... add all other endpoints
        }
        
        if endpoint in endpoint_mapping:
            return endpoint_mapping[endpoint]()
        else:
            console.print(f"[red]❌ Endpoint {endpoint} not implemented[/red]")
            return None
            
    except Exception as e:
        console.print(f"[red]❌ Error calling {endpoint}: {e}[/red]")
        return None
```

#### 3.4 Update cli/main.py

**Modify** token refresh logic:

```python
# Replace manual token checking with:
from cli.utils.api_client import refresh_token_if_needed

@app.callback()
def main():
    """CLI for interacting with the generated API client."""
    if not refresh_token_if_needed():
        console.print("[yellow]⚠️  Authentication may be required. Use 'auth get-token' if commands fail.[/yellow]")
```

#### 3.5 Testing Phase 3

```bash
# Test unified client
poetry run python -m cli.main auth get-token

# Test API operations
poetry run python -m cli.main system query-api

# Verify all operations use typed client
poetry run python -m cli.main system history
```

## Implementation Guidelines

### Code Quality Standards

1. **Type Hints**: All new code must include proper type annotations
2. **Error Handling**: Use try/catch blocks with proper logging
3. **Documentation**: Add docstrings to all public methods
4. **Testing**: Write unit tests for new functionality

### Testing Strategy

1. **Unit Tests**: Test state management independently
2. **Integration Tests**: Test CLI commands end-to-end
3. **Mock Tests**: Mock API client for command testing
4. **Error Cases**: Test authentication failures, network errors

### Rollback Strategy

Each phase should be implemented in separate branches:

```bash
git checkout -b refactor/phase-2-state-management
# Implement Phase 2
git checkout -b refactor/phase-3-api-client  
# Implement Phase 3
```

### Risk Assessment

**Phase 2 Risks:**
- **Medium**: State file corruption/permission issues
- **Low**: Migration of existing tokens/credentials

**Phase 3 Risks:**
- **High**: Breaking existing CLI commands
- **Medium**: API client method mapping complexity
- **Low**: Performance impact of typed client

### Success Criteria

**Phase 2 Complete When:**
- [ ] No dynamic writes to `.env` file
- [ ] All state stored in `~/.config/api-central/`
- [ ] Token refresh works without modifying `.env`
- [ ] All tests pass

**Phase 3 Complete When:**
- [ ] No direct `requests` calls in codebase
- [ ] All API operations use generated client
- [ ] `system query-api` command fully functional
- [ ] Type safety for all API interactions
- [ ] All tests pass

## Estimated Timeline

- **Phase 2**: 2-3 days (state management)
- **Phase 3**: 4-5 days (API client integration)
- **Testing & Polish**: 1-2 days

**Total**: 1-2 weeks for complete refactoring

## Additional Improvements (Post Phase 3)

1. **Add comprehensive error handling decorators**
2. **Implement command result caching**
3. **Add configuration validation**
4. **Improve CLI help and documentation**
5. **Add performance monitoring**
6. **Implement request retry logic**

---

*This document should be updated as each phase is completed to reflect actual implementation details and any discovered issues.*