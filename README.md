# API Central

Centralized CLI and SDK generator for OpenAPI-based APIs.

## Structure

- `openapi/`: OpenAPI specs
- `api_client/`: Auto-generated client SDK
- `cli/`: Typer CLI logic
- `scripts/`: Automation scripts
- `tests/`: Pytest-based test suites

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Regenerate client:
   ```bash
   python scripts/regen_client.py
   ```
3. Run CLI:
   ```bash
   python cli/main.py
   ``` 