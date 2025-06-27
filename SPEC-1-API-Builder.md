# SPEC-1-API-Builder

## Background

This project is an LLM-assisted API client and CLI builder using CursorAI. It automates generating Python SDKs and command-line interfaces from OpenAPI specifications, enabling rapid, testable, and maintainable API integration tooling. The approach combines auto-codegen with iterative AI prompts and developer-in-the-loop refinement.

---

## Requirements

- **Must Have**
  - Generate Python client SDK from OpenAPI via `openapi-python-client`
  - Provide CLI interface using `Typer`
  - Use `ruff`, `black`, `mypy` for linting and typing
  - Create `pyproject.toml` using `poetry`
  - Folder structure and documentation tailored for CursorAI iterative development
  - Include CI pipeline with lint, type-check, and test
  - Add TODO comments in scaffold files for CursorAI awareness

- **Should Have**
  - Auto-regenerate client SDK when OpenAPI file changes
  - Unit test stubs for each CLI command
  - Developer guide and coding rules

- **Could Have**
  - Async API support
  - Google Sheets output adapters
  
- **Won't Have (MVP)**
  - Web frontend
  - Multi-language client generation

---

## Method

### Folder Structure

```bash
api-central/  # TODO: Rename to api-builder if needed
├── openapi/                      # OpenAPI specs
│   └── example_api.yaml
├── api_client/                  # Auto-generated client SDK (via openapi-python-client)
│   └── ...
├── cli/                         # Typer CLI logic
│   ├── __init__.py
│   ├── main.py                  # Entry point
│   └── commands/
│       └── example.py           # Command modules
├── scripts/                     # Automation scripts
│   ├── regen_client.py          # Calls openapi-python-client
│   ├── watch_openapi.py         # Watches for OpenAPI file changes
│   └── patch_workspace.py       # Adds TODOs for Cursor
├── tests/                       # Pytest-based test suites
│   └── test_example.py
├── .github/
│   └── workflows/
│       └── ci.yaml              # Lint/type/test CI
├── pyproject.toml
├── README.md
└── .env.example
```

### CursorAI Guidelines

1. All folders and files pre-scaffolded with meaningful TODOs:
   - `### file: cli/main.py`
   - `# TODO: Implement auth logic`
2. All LLM prompts are scoped to a single module with rich context.
3. CI failures pasted back into CursorAI for patch recommendations.
4. Use the following template to generate or refine modules:

```text
You are completing this Python module as part of an API CLI builder tool. The module path is: `cli/commands/<command>.py`.

## Context:
- This CLI wraps a Python SDK generated from OpenAPI.
- Uses `Typer` for CLI structure.
- The client is located at `api_client/` and is imported where needed.
- Type hints, `black`, and `ruff` compliance required.
- Tests will be located in `tests/test_<command>.py`.

## Current task:
Implement a CLI command that performs <description of task>, calling the appropriate method from the API client.

## Constraints:
- Add TODOs for missing parts you cannot infer.
- Provide type-safe implementations.
- Avoid CLI-side retries or pagination logic for now.

## Examples:
Input: `mycli get-users --active`
Output: Calls `api_client.client.users.get_users(active=True)`, prints summary table.

## File start
### file: cli/commands/<command>.py
```

### Conventions

- All code must use type hints.
- All code must pass `ruff`, `black`, `mypy`, and `pytest`.
- Do not commit generated clients. Use `.gitignore`.

### Project Rules

- Regenerate SDKs using:
```bash
python scripts/regen_client.py
```
- Auto-regenerate SDKs when OpenAPI changes using:
```bash
python scripts/watch_openapi.py
```
- Validate with:
```bash
poetry run ruff . && poetry run mypy . && poetry run pytest
```
- Use `Typer` for all CLI commands and subcommands.

### References

- https://github.com/openapi-generators/openapi-python-client
- https://typer.tiangolo.com/
- https://docs.cursor.sh/
- https://beta.ruff.rs/docs/

---

## Milestones

### Phase 1: Scaffold Core Project
- Create base folder structure.
- Add placeholder files with `### file:` headers and TODOs.
- Generate `pyproject.toml` with `poetry init`.
- Configure `.gitignore`, `.env.example`, and `README.md`.

### Phase 2: Automate SDK Generation
- Implement `scripts/regen_client.py`
- Implement `scripts/watch_openapi.py` using `watchdog` to call above script on file change.

### Phase 3: CLI Entry + First Command
- Create `cli/main.py` with basic Typer app.
- Create `cli/commands/example.py` with a stub CLI command.

### Phase 4: Add Testing + CI
- Add `tests/test_example.py` with simple `CliRunner` test.
- Write `.github/workflows/ci.yaml` to run:
  - `ruff .`
  - `mypy .`
  - `pytest`

### Phase 5: Patch & Iterate
- Use Cursor to fill out command implementations.
- Add real test cases.
- Refine logic iteratively via prompt cycle.

---

## Gathering Results

### ✅ Functional Acceptance Criteria
- CLI commands run successfully against the generated client.
- All required fields and flags from the OpenAPI spec are correctly surfaced in CLI.
- The CLI output formats (e.g., JSON, tables) are consistent and clear.
- Watcher script reacts to changes and regenerates SDK reliably.

### ✅ Code Quality and Maintainability
- All modules pass lint (`ruff`), type checks (`mypy`), and tests (`pytest`).
- CursorAI prompt cycles result in clear, readable, and tested Python modules.
- Each CLI module is isolated and testable.

### ✅ Development Workflow Validation
- Adding new CLI commands requires only 1–2 prompt iterations in Cursor.
- CI runs clean on every commit.
- Developer documentation is followed with minimal confusion.

---

# TODO: Add more detailed developer guide and coding rules as project evolves.
# TODO: Add async API and Google Sheets adapter examples if/when implemented. 