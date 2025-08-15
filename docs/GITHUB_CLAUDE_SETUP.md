# Setting Up Claude Code Directly in GitHub

## 🚀 Claude for GitHub Integration

GitHub now offers direct Claude integration, allowing you to launch Claude Code sessions directly from your repository. This is the most efficient way to manage multiple agents working on your project.

## 📦 Installation

### Step 1: Install Claude for GitHub

1. Go to [GitHub Marketplace - Claude](https://github.com/marketplace/claude-for-github)
2. Click "Install" or "Configure"
3. Select your repository: `cvanleer/api-builder`
4. Grant necessary permissions

### Step 2: Enable Claude in Your Repository

1. Navigate to your repository: [github.com/cvanleer/api-builder](https://github.com/cvanleer/api-builder)
2. Go to **Settings** → **GitHub Apps**
3. Configure Claude with appropriate permissions

## 🎯 Launching Claude Agents from GitHub

### Method 1: From Pull Requests (Recommended)

1. **Create a PR for each feature branch**:
   ```bash
   # Already created:
   - feature/testing-infrastructure
   - feature/multi-format-parsers
   - feature/error-handling
   - feature/documentation
   ```

2. **In each PR, use Claude commands**:
   ```
   @claude-ai please implement the testing infrastructure according to TODO.md Week 1 tasks
   ```

3. **Claude will**:
   - Analyze the branch
   - Understand the context
   - Make commits directly to the PR
   - Respond with progress updates

### Method 2: From Issues

1. **Create focused issues for each agent**:

   **Issue #1: Testing Infrastructure**
   ```markdown
   @claude-ai Please work on the testing infrastructure:
   - Branch: feature/testing-infrastructure
   - Tasks: See TODO.md Week 1
   - Focus: Unit tests for dependency_analyzer and parameter_detector
   - Goal: 80% test coverage
   ```

   **Issue #2: Parser Development**
   ```markdown
   @claude-ai Please implement multi-format parsers:
   - Branch: feature/multi-format-parsers
   - Create Postman and Insomnia parsers
   - Follow the Parser protocol in parsers/__init__.py
   - Include tests for each parser
   ```

### Method 3: From Code Comments

1. **Add TODO comments in code**:
   ```python
   # @claude-ai: Implement exponential backoff with jitter
   def exponential_backoff():
       pass
   ```

2. **Claude will scan for these comments and create PRs**

## 🤖 Multi-Agent Workflow in GitHub

### Setting Up Parallel Agents

1. **Create a Project Board**:
   - Go to Projects tab in your repo
   - Create "API Builder Development"
   - Add columns: Agent 1, Agent 2, Agent 3, Agent 4, Review, Done

2. **Create Agent-Specific Labels**:
   ```
   agent-1-testing
   agent-2-parsers
   agent-3-errors
   agent-4-docs
   ```

3. **Launch All Agents Simultaneously**:

   Create 4 issues with these exact texts:

   **Issue: Launch Testing Agent**
   ```markdown
   @claude-ai You are Agent 1 (Testing Specialist)
   
   Please checkout feature/testing-infrastructure and:
   1. Set up pytest infrastructure with fixtures
   2. Write unit tests for cli/dependency_analyzer.py (90% coverage)
   3. Write unit tests for cli/parameter_detector.py (90% coverage)
   4. Create mock API responses in tests/fixtures/
   5. Set up pytest-cov for coverage reporting
   
   Follow existing patterns. Check TODO.md Week 1.
   Create a PR when you have significant progress.
   ```

   **Issue: Launch Parser Agent**
   ```markdown
   @claude-ai You are Agent 2 (Parser Developer)
   
   Please checkout feature/multi-format-parsers and:
   1. Complete APISpecification in parsers/__init__.py
   2. Implement PostmanParser in parsers/postman.py
   3. Implement InsomniaParser in parsers/insomnia.py
   4. Create parser factory for format detection
   5. Write tests for each parser
   
   All parsers must implement the Parser protocol.
   Reference docs/ARCHITECTURE.md for patterns.
   ```

   **Issue: Launch Error Handling Agent**
   ```markdown
   @claude-ai You are Agent 3 (Error Handling Engineer)
   
   Please checkout feature/error-handling and:
   1. Complete qapi/retry.py with exponential backoff
   2. Implement circuit breaker pattern
   3. Create qapi/exceptions.py with custom exceptions
   4. Add comprehensive logging throughout
   5. Implement graceful degradation
   
   Include: APIConnectionError, AuthenticationError, RateLimitError
   Follow Python error handling best practices.
   ```

   **Issue: Launch Documentation Agent**
   ```markdown
   @claude-ai You are Agent 4 (Documentation Writer)
   
   Please checkout feature/documentation and:
   1. Add Google-style docstrings to all public functions
   2. Create docs/USER_GUIDE.md with tutorials
   3. Set up Sphinx documentation
   4. Create examples/ directory with sample scripts
   5. Write docs/TROUBLESHOOTING.md
   
   Make the project approachable for new users.
   Include code examples in all documentation.
   ```

## 🎨 GitHub Claude Commands

### Basic Commands
```bash
# In any issue or PR comment:
@claude-ai analyze this code
@claude-ai fix the failing tests
@claude-ai implement the TODO items
@claude-ai review this PR
@claude-ai suggest improvements
```

### Advanced Commands
```bash
# Specific file operations
@claude-ai edit cli/main.py and add error handling
@claude-ai create tests/test_parser.py with unit tests
@claude-ai refactor this function for better performance

# Branch operations
@claude-ai checkout feature/testing-infrastructure and run tests
@claude-ai merge develop into this branch
@claude-ai resolve merge conflicts

# Complex tasks
@claude-ai implement the tasks in TODO.md for Week 1
@claude-ai follow the architecture in docs/ARCHITECTURE.md
@claude-ai ensure 80% test coverage for this module
```

## 📊 Monitoring Agent Progress

### GitHub Dashboard View

1. **Actions Tab**: See CI/CD runs for each push
2. **Pull Requests**: Track each agent's PR
3. **Issues**: See agent conversations
4. **Projects**: Kanban board of progress
5. **Insights**: Contribution graphs

### Coordination Commands

**In the main issue, coordinate all agents**:
```markdown
@claude-ai status report for all agents
@claude-ai merge all feature branches to develop
@claude-ai run integration tests across all branches
@claude-ai identify conflicts between agent work
```

## 🔄 Automated Workflows

### Create `.github/workflows/claude-agents.yml`:

```yaml
name: Claude Agent Automation

on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]

jobs:
  dispatch-to-claude:
    if: contains(github.event.comment.body, '@claude-ai')
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Claude
        uses: anthropic/claude-github-action@v1
        with:
          task: ${{ github.event.comment.body }}
          branch: ${{ github.head_ref }}
          
  weekly-sync:
    schedule:
      - cron: '0 9 * * MON'  # Weekly Monday 9am
    runs-on: ubuntu-latest
    steps:
      - name: Weekly Agent Sync
        run: |
          echo "@claude-ai provide weekly progress report" >> $GITHUB_STEP_SUMMARY
```

## 🎯 Best Practices

### DO's:
- ✅ Create separate branches for each agent
- ✅ Use clear, specific instructions
- ✅ Reference documentation files
- ✅ Set measurable goals (coverage %, tasks)
- ✅ Use labels for organization
- ✅ Review agent PRs before merging

### DON'Ts:
- ❌ Don't have multiple agents on same branch
- ❌ Don't give vague instructions
- ❌ Don't skip code review
- ❌ Don't merge without tests
- ❌ Don't overlap agent responsibilities

## 🚦 Quick Start Checklist

- [ ] Install Claude for GitHub from Marketplace
- [ ] Create 4 feature branches (✅ already done)
- [ ] Create 4 issues with agent prompts
- [ ] Add @claude-ai mention to launch each agent
- [ ] Create Project board for tracking
- [ ] Set up labels for organization
- [ ] Monitor PRs as they're created
- [ ] Review and merge completed work

## 💡 Pro Tips

1. **Batch Operations**: 
   ```markdown
   @claude-ai run all tests and fix any failures
   ```

2. **Context Sharing**:
   ```markdown
   @claude-ai Agent 2 has created parsers in PR #5. Please make your tests compatible.
   ```

3. **Incremental Progress**:
   ```markdown
   @claude-ai commit your progress so far and create a draft PR
   ```

4. **Code Review**:
   ```markdown
   @claude-ai review the changes from Agent 1 and suggest improvements
   ```

## 🔗 Useful Links

- [Claude for GitHub Documentation](https://docs.anthropic.com/claude/docs/claude-for-github)
- [GitHub Actions with Claude](https://github.com/marketplace/actions/claude-ai)
- [Your Repository](https://github.com/cvanleer/api-builder)
- [Project Board](https://github.com/cvanleer/api-builder/projects)

## 🎉 Benefits of GitHub Integration

1. **No Local Setup**: Agents work directly in GitHub
2. **Automatic PRs**: Changes are automatically in PRs
3. **Built-in Review**: GitHub's review tools
4. **CI/CD Integration**: Tests run automatically
5. **Collaboration**: Easy to see all agent work
6. **History**: Complete audit trail
7. **Rollback**: Easy to revert changes

---

*With GitHub integration, you're commanding an army of AI developers directly from your repository!*