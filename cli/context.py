import json
from pathlib import Path
from typing import Optional

CONTEXT_PATH = Path.home() / ".tattle-cli" / "context.json"
CONTEXT_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_context() -> dict:
    if CONTEXT_PATH.exists():
        with open(CONTEXT_PATH) as f:
            return json.load(f)
    return {}

def save_context(data: dict):
    existing = get_context()
    existing.update(data)
    with open(CONTEXT_PATH, "w") as f:
        json.dump(existing, f, indent=2)

def get_value(key: str) -> Optional[str]:
    return get_context().get(key)

def clear_context():
    CONTEXT_PATH.unlink(missing_ok=True)

def list_context():
    return get_context() 