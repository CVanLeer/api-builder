"""Context management utilities for the CLI app."""
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime

CONTEXT_PATH = Path.home() / ".tattle-cli" / "context.json"
HISTORY_PATH = Path.home() / ".tattle-cli" / "history.json"
CONTEXT_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_context() -> dict:
    """Load the current context from disk."""
    if CONTEXT_PATH.exists():
        with open(CONTEXT_PATH) as f:
            return json.load(f)
    return {}

def save_context(data: dict):
    """Update and save the context to disk."""
    existing = get_context()
    existing.update(data)
    with open(CONTEXT_PATH, "w") as f:
        json.dump(existing, f, indent=2)

def get_value(key: str) -> Optional[str]:
    """Get a value from the context by key."""
    return get_context().get(key)

def clear_context():
    """Clear the saved context file."""
    CONTEXT_PATH.unlink(missing_ok=True)

def list_context():
    """Return the current context as a dict."""
    return get_context()

# Command History Functions
def save_command_to_history(endpoint: str, params: dict, success: bool = True):
    """Save a command to history."""
    history = get_command_history()
    
    command_entry = {
        "timestamp": datetime.now().isoformat(),
        "endpoint": endpoint,
        "parameters": params,
        "success": success
    }
    
    # Add to beginning of history
    history.insert(0, command_entry)
    
    # Keep only last 50 commands
    history = history[:50]
    
    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)

def get_command_history() -> List[dict]:
    """Get command history."""
    if HISTORY_PATH.exists():
        with open(HISTORY_PATH) as f:
            return json.load(f)
    return []

def clear_command_history():
    """Clear command history."""
    HISTORY_PATH.unlink(missing_ok=True)

def get_recent_commands(limit: int = 10) -> List[dict]:
    """Get recent commands."""
    history = get_command_history()
    return history[:limit]

def replay_command(history_index: int) -> Optional[dict]:
    """Get command from history by index for replay."""
    history = get_command_history()
    if 0 <= history_index < len(history):
        return history[history_index]
    return None 