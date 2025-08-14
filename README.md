# API Builder 🚀

> An intelligent, automated API integration platform that transforms any API documentation into a working Python SDK with CLI interface.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/dependency%20management-poetry-blueviolet)](https://python-poetry.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue)](http://mypy-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Project Vision

API Builder eliminates the manual work of API integration by automatically:
- Parsing any API documentation format (OpenAPI, Postman, or plain text)
- Generating type-safe Python SDKs
- Resolving complex parameter dependencies
- Creating intelligent CLI interfaces
- Executing multi-step API workflows automatically

## 📊 Current Status

**Phase**: Prototype (60% Complete)  
**Stability**: Alpha  
**Test Coverage**: <5% ⚠️  

See [PROJECT_STATUS.md](./PROJECT_STATUS.md) for detailed metrics.

## ✨ Features

### Working Today
- ✅ **OpenAPI SDK Generation** - Automatic client generation from OpenAPI specs
- ✅ **Smart Parameter Detection** - Identifies foreign keys, dates, enums automatically
- ✅ **Dependency Analysis** - Maps relationships between API endpoints
- ✅ **Secure Credential Storage** - Encrypted storage of API keys and tokens
- ✅ **Interactive CLI** - Rich terminal interface with progress tracking
- ✅ **Command History** - Record and replay API calls

### Coming Soon
- 🚧 Multi-format support (Postman, Insomnia, plain docs)
- 🚧 LLM-powered documentation parsing
- 🚧 Natural language API interaction
- 🚧 Automated workflow execution
- 🚧 Plugin system for extensibility

## 🚀 Quick Start

### Prerequisites

- Python 3.12+ (recommend using [pyenv](https://github.com/pyenv/pyenv))
- [Poetry](https://python-poetry.org/) for dependency management

### Installation

```bash
# Clone the repository
git clone https://github.com/cvanleer/api-builder.git
cd api-builder

# Install dependencies
poetry install

# Activate the virtual environment
poetry shell
```

### Basic Usage

1. **Place your OpenAPI spec** in `openapi/openai.json`

2. **Generate the API client**:
   ```bash
   poetry run python scripts/regen_client.py
   ```

3. **Authenticate**:
   ```bash
   poetry run python cli/main.py auth get-token
   ```

4. **Explore the API**:
   ```bash
   # Interactive API explorer
   poetry run python cli/main.py system query-api
   
   # Or use the interactive terminal
   poetry run python interactive_terminal.py
   ```

### Example Commands

```bash
# Show command history
poetry run python cli/main.py system history

# Replay a previous command
poetry run python cli/main.py system replay 0

# Set default parameters
poetry run python cli/main.py system set-defaults
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│            CLI Interface (Typer)         │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│         QAPI Orchestration Layer         │
└────────────────────┬────────────────────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
┌────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│Dependency │ │ Parameter  │ │   State    │
│ Analyzer  │ │  Detector  │ │  Manager   │
└───────────┘ └────────────┘ └────────────┘
                     │
            ┌────────▼────────┐
            │ Auto-Generated  │
            │   API Client    │
            └─────────────────┘
```

See [ARCHITECTURE.md](./docs/ARCHITECTURE.md) for detailed design documentation.

## 📋 Development Roadmap

### Phase 1: Foundation (Current)
- [ ] Comprehensive test suite
- [ ] Robust error handling
- [ ] CI/CD pipeline

### Phase 2: Multi-Format Support
- [ ] Postman collection parser
- [ ] LLM documentation parser
- [ ] Custom format plugins

### Phase 3: Intelligent Automation
- [ ] Natural language interface
- [ ] Workflow templates
- [ ] Automatic optimization

See [ROADMAP.md](./docs/ROADMAP.md) for the complete development plan.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for:
- Development setup
- Code style guidelines
- Testing requirements
- Pull request process

### Good First Issues
Look for issues labeled `good-first-issue` in our [GitHub Issues](https://github.com/cvanleer/api-builder/issues).

## 📚 Documentation

- [Project Status](./PROJECT_STATUS.md) - Current state and metrics
- [Architecture](./docs/ARCHITECTURE.md) - System design and patterns
- [Roadmap](./docs/ROADMAP.md) - Development timeline
- [TODO List](./TODO.md) - Detailed task tracking
- [API Reference](./docs/API.md) - Code documentation

## 🧪 Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=cli --cov=qapi

# Type checking
poetry run mypy .

# Linting
poetry run ruff check .
```

## 🔧 Configuration

Create a `.env` file in the project root:

```env
API_BASE_URL=https://api.example.com
API_KEY=your_api_key_here
```

## 📈 Project Status

| Metric | Current | Target |
|--------|---------|--------|
| Test Coverage | <5% | 80% |
| Type Coverage | 70% | 95% |
| Documentation | 40% | 90% |
| Performance | ~500ms | <100ms |

## 🚨 Known Issues

- Circular dependency detection needs improvement
- Test coverage is critically low
- Some error messages need better formatting

See our [issue tracker](https://github.com/cvanleer/api-builder/issues) for all known issues.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Typer](https://typer.tiangolo.com/) for CLI
- Uses [openapi-python-client](https://github.com/openapi-generators/openapi-python-client) for SDK generation
- Terminal UI powered by [Rich](https://rich.readthedocs.io/)

## 📬 Contact

- **Issues**: [GitHub Issues](https://github.com/cvanleer/api-builder/issues)
- **Discussions**: [GitHub Discussions](https://github.com/cvanleer/api-builder/discussions)

---

**⭐ If you find this project useful, please consider giving it a star on GitHub!** 