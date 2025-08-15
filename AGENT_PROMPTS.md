# Claude Code Agent Prompts for API Builder

Copy and paste these prompts into separate Claude Code sessions for parallel development.

## 🧪 Agent 1: Testing & Quality Assurance

```
I need you to work on the api-builder project from GitHub (cvanleer/api-builder).

Please work on the feature/testing-infrastructure branch and focus on building comprehensive test coverage.

Your tasks:
1. Set up pytest infrastructure with fixtures and mocks
2. Write unit tests for cli/dependency_analyzer.py (aim for 90% coverage)
3. Write unit tests for cli/parameter_detector.py (aim for 90% coverage)
4. Create mock API responses in tests/fixtures/
5. Set up pytest-cov for coverage reporting
6. Write integration tests for the authentication flow

Follow these guidelines:
- Use pytest fixtures for reusable test data
- Mock external API calls
- Follow the existing code patterns
- Add docstrings to all test functions
- Group related tests in classes

Check TODO.md Week 1 section for specific testing tasks.
The goal is to achieve 80%+ test coverage for all modules you work on.
```

## 🔄 Agent 2: Multi-Format Parser Development

```
I need you to work on the api-builder project from GitHub (cvanleer/api-builder).

Please work on the feature/multi-format-parsers branch and implement support for multiple API documentation formats.

Your tasks:
1. Complete the APISpecification dataclass in parsers/__init__.py
2. Create parsers/postman.py with PostmanParser class
3. Create parsers/insomnia.py with InsomniaParser class  
4. Create parsers/openapi.py to refactor existing OpenAPI logic
5. Implement parsers/factory.py for automatic format detection
6. Write comprehensive tests for each parser

Design requirements:
- All parsers must implement the Parser protocol
- Convert all formats to unified APISpecification model
- Include confidence scoring for parsed data
- Handle malformed inputs gracefully
- Support both JSON and YAML formats where applicable

Reference docs/ARCHITECTURE.md for the parser design patterns.
Coordinate with Agent 1 who will be testing your parsers.
```

## 🛡️ Agent 3: Error Handling & Resilience

```
I need you to work on the api-builder project from GitHub (cvanleer/api-builder).

Please work on the feature/error-handling branch and implement robust error handling throughout the application.

Your tasks:
1. Complete qapi/retry.py with exponential backoff implementation
2. Implement circuit breaker pattern in qapi/retry.py
3. Create qapi/exceptions.py with custom exception hierarchy
4. Add comprehensive logging using Python's logging module
5. Implement graceful degradation for network failures
6. Add user-friendly error messages throughout CLI

Requirements:
- Exponential backoff with jitter
- Circuit breaker with half-open state
- Structured logging with contextual information
- Error recovery strategies for common failures
- Rate limiting respect with 429 handling
- Timeout handling for slow endpoints

Create these custom exceptions:
- APIConnectionError
- AuthenticationError  
- RateLimitError
- ParseError
- ValidationError

Ensure all error handling follows Python best practices.
```

## 📚 Agent 4: Documentation & Developer Experience

```
I need you to work on the api-builder project from GitHub (cvanleer/api-builder).

Please work on the feature/documentation branch and create comprehensive documentation.

Your tasks:
1. Add Google-style docstrings to ALL public functions
2. Create docs/USER_GUIDE.md with step-by-step tutorials
3. Set up Sphinx documentation in docs/api/
4. Create examples/ directory with sample scripts
5. Write docs/TROUBLESHOOTING.md for common issues
6. Update README.md with better examples and badges

Documentation requirements:
- Every public function needs a docstring
- Include code examples in docstrings
- Create at least 5 example scripts showing different use cases
- User guide should cover basic to advanced usage
- Include screenshots/GIFs where helpful
- Add type hints to all function signatures

Also improve developer experience:
- Add helpful error messages
- Improve CLI help text
- Add progress indicators for long operations
- Create shell completion scripts

Make the project approachable for new users and contributors.
```

## 🎯 Coordination Agent (Human or AI)

```
I'm coordinating multiple Claude agents working on the api-builder project.

Current agents:
- Agent 1: Testing (feature/testing-infrastructure)
- Agent 2: Parsers (feature/multi-format-parsers)  
- Agent 3: Error Handling (feature/error-handling)
- Agent 4: Documentation (feature/documentation)

Please help me:
1. Review pull requests from each agent
2. Identify potential conflicts between branches
3. Suggest integration points
4. Track progress against TODO.md
5. Merge feature branches to develop branch
6. Ensure all agents are following project standards

Monitor the GitHub repository and provide weekly progress reports.
```

## 🚀 Quick Start Commands for Each Agent

### Setup commands for all agents:
```bash
# Clone and setup
git clone https://github.com/cvanleer/api-builder.git
cd api-builder
poetry install

# Switch to your assigned branch
git checkout feature/[your-branch-name]

# Create your working directory
mkdir -p [your-work-area]

# Run tests frequently
poetry run pytest

# Check your changes
git status
git diff

# Commit with descriptive messages
git add .
git commit -m "feat(area): description of change"
git push
```

### Agent-specific directories:
- Agent 1: Focus on `tests/` directory
- Agent 2: Focus on `parsers/` directory  
- Agent 3: Focus on `qapi/` directory
- Agent 4: Focus on `docs/` and `examples/` directories

## 📋 Daily Standup Template

Each agent should provide daily updates:

```
## Agent N Daily Update - [Date]

### Completed Today:
- Task 1
- Task 2

### In Progress:
- Task 3 (60% complete)

### Blocked By:
- Need input on X from Agent Y

### Tomorrow's Plan:
- Complete Task 3
- Start Task 4

### PR Status:
- PR #123 ready for review
- PR #124 in progress
```

## 🔗 Communication

- Use PR comments for code-specific discussions
- Create GitHub Issues for blockers
- Tag relevant agents in comments using @mentions
- Keep commits small and focused
- Write clear commit messages

Remember: The goal is parallel progress without conflicts!