"""Context management utilities for the CLI app."""
import json
from pathlib import Path
from typing import Optional

CONTEXT_PATH = Path.home() / ".tattle-cli" / "context.json"
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