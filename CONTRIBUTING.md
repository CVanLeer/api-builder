# Contributing to API Builder

Thank you for your interest in contributing to API Builder! This document provides guidelines and instructions for contributing to the project.

## 🤝 Code of Conduct

By participating in this project, you agree to:
- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Accept feedback gracefully

## 🚀 Getting Started

### Prerequisites

- Python 3.12+ (managed with pyenv recommended)
- Poetry for dependency management
- Git for version control
- GitHub account

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/api-builder.git
   cd api-builder
   ```

2. **Install Dependencies**
   ```bash
   poetry install --with dev
   ```

3. **Activate Environment**
   ```bash
   poetry shell
   ```

4. **Run Tests**
   ```bash
   poetry run pytest
   ```

5. **Check Code Quality**
   ```bash
   poetry run ruff check .
   poetry run mypy .
   ```

## 📝 Development Workflow

### 1. Find or Create an Issue

- Check existing issues in GitHub
- Create a new issue if needed
- Comment on the issue to claim it

### 2. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 3. Make Your Changes

- Write clean, readable code
- Add type hints to all functions
- Follow existing code patterns
- Update tests as needed
- Update documentation

### 4. Test Your Changes

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_specific.py

# Run with coverage
poetry run pytest --cov=cli --cov=qapi
```

### 5. Check Code Quality

```bash
# Format code
poetry run black .

# Check linting
poetry run ruff check .

# Check types
poetry run mypy .
```

### 6. Commit Your Changes

```bash
# Use conventional commits
git commit -m "feat: add new parser for Postman collections"
git commit -m "fix: resolve circular dependency in parameter resolution"
git commit -m "docs: update API documentation"
git commit -m "test: add unit tests for state manager"
```

### 7. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## 📋 Pull Request Guidelines

### PR Title Format

Use conventional commit format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions or changes
- `refactor:` Code refactoring
- `perf:` Performance improvements
- `chore:` Maintenance tasks

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] No new warnings
```

## 🎨 Code Style Guidelines

### Python Style

- Follow PEP 8 with 88-character line length (Black default)
- Use meaningful variable names
- Add docstrings to all public functions
- Use type hints everywhere

### Example Function

```python
from typing import Optional, List, Dict, Any

def analyze_endpoint(
    endpoint_path: str,
    parameters: List[Dict[str, Any]],
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    Analyze an API endpoint and its parameters.
    
    Args:
        endpoint_path: The API endpoint path (e.g., "/users/{id}")
        parameters: List of parameter definitions
        timeout: Optional timeout in seconds
        
    Returns:
        Dictionary containing analysis results
        
    Raises:
        ValueError: If endpoint_path is invalid
        TimeoutError: If analysis exceeds timeout
    """
    # Implementation here
    pass
```

### Import Order

1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# Standard library
import json
from typing import Optional

# Third-party
import typer
from pydantic import BaseModel

# Local
from cli.config import settings
from qapi.session import QAPISession
```

## 🧪 Testing Guidelines

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch

class TestFeatureName:
    """Test suite for FeatureName."""
    
    @pytest.fixture
    def sample_data(self):
        """Provide sample data for tests."""
        return {"key": "value"}
    
    def test_normal_case(self, sample_data):
        """Test normal operation."""
        assert something == expected
    
    def test_edge_case(self):
        """Test edge cases."""
        with pytest.raises(ValueError):
            function_that_should_fail()
    
    @patch('module.external_service')
    def test_with_mock(self, mock_service):
        """Test with mocked dependencies."""
        mock_service.return_value = "mocked"
        assert function_under_test() == "expected"
```

### Test Coverage Requirements

- New features: 80% coverage minimum
- Bug fixes: Include regression test
- Critical paths: 100% coverage

## 📚 Documentation Guidelines

### Code Documentation

- All public APIs must have docstrings
- Use Google-style docstrings
- Include examples for complex functions

### User Documentation

- Update README.md for user-facing changes
- Update relevant docs/ files
- Include examples and use cases

### Commit Messages

Good commit messages:
```
feat: add support for GraphQL schema parsing

- Implement GraphQLParser class
- Add schema introspection support
- Include tests and documentation
```

Bad commit messages:
```
fixed stuff
update
WIP
```

## 🏗️ Architecture Decisions

When making significant architectural changes:

1. Create an Architecture Decision Record (ADR)
2. Place it in `docs/adr/`
3. Use the template:

```markdown
# ADR-001: Title

## Status
Proposed/Accepted/Deprecated

## Context
What is the issue we're addressing?

## Decision
What have we decided to do?

## Consequences
What are the results of this decision?
```

## 🐛 Reporting Issues

### Bug Reports

Include:
- Python version
- OS and version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error messages/stack traces

### Feature Requests

Include:
- Use case description
- Proposed solution
- Alternative solutions considered
- Impact on existing functionality

## 🎯 Areas for Contribution

### Good First Issues

Look for issues labeled:
- `good-first-issue`
- `help-wanted`
- `documentation`

### High Priority Areas

1. **Testing**: Increase test coverage
2. **Documentation**: Improve user guides
3. **Parsers**: Add new format support
4. **Performance**: Optimize slow operations
5. **UI/UX**: Improve CLI experience

## 📬 Communication

- **Issues**: GitHub Issues for bugs and features
- **Discussions**: GitHub Discussions for questions
- **Pull Requests**: For code contributions

## 🙏 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Given credit in documentation

## ⚖️ License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT).

---

Thank you for contributing to API Builder! Your efforts help make API integration easier for everyone. 🎉