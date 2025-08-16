# API Builder Troubleshooting Guide

This guide helps you diagnose and fix common issues with API Builder.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Authentication Issues](#authentication-issues)
- [API Connection Problems](#api-connection-problems)
- [Dependency Resolution Issues](#dependency-resolution-issues)
- [Performance Problems](#performance-problems)
- [Client Generation Errors](#client-generation-errors)
- [Installation Issues](#installation-issues)
- [FAQ](#faq)
- [Debug Tips](#debug-tips)
- [Getting Help](#getting-help)

## Quick Diagnostics

Run this checklist first to identify common issues:

```bash
# 1. Check Python version
python --version
# Should be 3.12+

# 2. Verify Poetry installation
poetry --version
# Should show Poetry version

# 3. Check dependencies
poetry check
# Should show "All dependencies are up to date"

# 4. Test basic CLI
poetry run python cli/main.py --help
# Should show help menu

# 5. Check authentication
poetry run python cli/main.py auth get-token
# Should prompt for credentials
```

## Authentication Issues

### ❌ "Authentication failed"

**Symptoms:**
- `❌ Authentication failed.` message after entering credentials
- Unable to make API calls

**Causes & Solutions:**

1. **Incorrect Credentials**
   ```bash
   # Solution: Verify your credentials
   poetry run python cli/main.py auth get-token
   # Double-check email and password
   ```

2. **API Endpoint Changed**
   ```bash
   # Check your .env file
   cat .env
   # Verify API_BASE_URL is correct
   ```

3. **Network Issues**
   ```bash
   # Test API connectivity
   curl -X POST $API_BASE_URL/auth/token \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"test"}'
   ```

### ❌ "No authentication token found"

**Symptoms:**
- Error when trying to make API calls
- CLI doesn't prompt for authentication

**Solutions:**

1. **Get New Token**
   ```bash
   poetry run python cli/main.py auth get-token
   ```

2. **Check Token Storage**
   ```bash
   # Check if state files exist
   ls -la ~/.api-builder/
   # Should show token and credential files
   ```

3. **Reset Authentication**
   ```bash
   # Remove stored credentials
   rm -rf ~/.api-builder/
   # Get new token
   poetry run python cli/main.py auth get-token
   ```

## API Connection Problems

### ❌ "Unable to connect to the API"

**Symptoms:**
- Connection timeout errors
- "Connection refused" messages

**Solutions:**

1. **Check API URL**
   ```bash
   # Verify API_BASE_URL in .env
   echo $API_BASE_URL
   # Try accessing in browser
   curl $API_BASE_URL/health
   ```

2. **Network Connectivity**
   ```bash
   # Test internet connection
   ping google.com
   
   # Test specific API host
   ping api.example.com
   ```

3. **Firewall/Proxy Issues**
   ```bash
   # Check proxy settings
   echo $HTTP_PROXY
   echo $HTTPS_PROXY
   
   # Test without proxy
   unset HTTP_PROXY HTTPS_PROXY
   ```

### ❌ "HTTP 404 - Endpoint not found"

**Symptoms:**
- Specific endpoints return 404 errors
- API client method not found

**Solutions:**

1. **Regenerate API Client**
   ```bash
   poetry run python scripts/regen_client.py
   ```

2. **Check OpenAPI Spec**
   ```bash
   # Validate your OpenAPI spec
   python -c "import json; json.load(open('openapi/openai.json'))"
   ```

3. **Verify Endpoint Paths**
   ```bash
   # List available endpoints
   poetry run python cli/main.py system query-api
   # Check if endpoint exists in list
   ```

## Dependency Resolution Issues

### ❌ "No provider found for parameter"

**Symptoms:**
- API Builder can't automatically resolve parameter values
- Manual input required for all parameters

**Solutions:**

1. **Check Parameter Naming**
   ```bash
   # Common parameter name patterns:
   # merchantId -> /merchants
   # locationId -> /locations
   # userId -> /users
   ```

2. **Add Custom Mapping**
   ```python
   # Edit cli/parameter_detector.py
   self.reference_patterns: Dict[str, str] = {
       'customId': 'custom_endpoint',
       # Add your parameter mappings
   }
   ```

3. **Manual Parameter Resolution**
   ```bash
   # Provide values manually when prompted
   # Or use set-defaults command
   poetry run python cli/main.py system set-defaults
   ```

### ❌ "Circular dependency detected"

**Symptoms:**
- Warning about circular dependencies
- Infinite loops in parameter resolution

**Solutions:**

1. **Check Dependency Chain**
   ```bash
   # Review your OpenAPI spec for circular references
   # Example: /merchants needs locationId, /locations needs merchantId
   ```

2. **Break the Chain**
   - Provide one parameter manually
   - Use cached values from previous calls
   - Update OpenAPI spec to remove circular dependencies

### ❌ "Could not extract ID from selection"

**Symptoms:**
- Parameter selection interface shows data but can't extract IDs
- "Could not extract merchantId from selection" errors

**Solutions:**

1. **Check Response Format**
   ```bash
   # Review API response structure
   # Ensure ID fields are named consistently (id, Id, merchantId)
   ```

2. **Add Custom ID Extraction**
   ```python
   # Edit cli/parameter_detector.py
   def extract_id_from_response(self, response, param_name):
       # Add custom logic for your API response format
   ```

## Performance Problems

### 🐌 "Slow API responses"

**Symptoms:**
- Long wait times for API calls
- Timeout errors

**Solutions:**

1. **Check Network Latency**
   ```bash
   # Test API response times
   time curl $API_BASE_URL/merchants
   ```

2. **Optimize Pagination**
   ```bash
   # Use smaller page sizes
   # Limit number of auto-fetched pages
   ```

3. **Enable Caching**
   - API Builder caches parameter values within sessions
   - Use `system history` and `system replay` for repeated calls

### 🔄 "Too many API calls"

**Symptoms:**
- Rate limit errors (HTTP 429)
- Slow dependency resolution

**Solutions:**

1. **Use Cached Values**
   ```bash
   # Check what's already cached
   poetry run python cli/main.py system history
   
   # Replay previous successful calls
   poetry run python cli/main.py system replay 0
   ```

2. **Set Default Values**
   ```bash
   # Pre-populate common parameters
   poetry run python cli/main.py system set-defaults
   ```

## Client Generation Errors

### ❌ "openapi-python-client failed"

**Symptoms:**
- Client generation script fails
- Import errors for generated client

**Solutions:**

1. **Validate OpenAPI Spec**
   ```bash
   # Check JSON validity
   python -c "import json; json.load(open('openapi/openai.json'))"
   
   # Use online validator
   # Copy spec content to https://editor.swagger.io/
   ```

2. **Check OpenAPI Version**
   ```bash
   # API Builder supports OpenAPI 3.0+
   # Check "openapi" field in your spec
   grep -A1 '"openapi"' openapi/openai.json
   ```

3. **Fix Common Spec Issues**
   ```yaml
   # Ensure all required fields are present
   openapi: "3.0.0"
   info:
     title: "Your API"
     version: "1.0.0"
   servers:
     - url: "https://api.example.com"
   ```

### ❌ "ModuleNotFoundError: No module named 'gettattle_api_client'"

**Symptoms:**
- Import errors when trying to use generated client
- Client not found in Python path

**Solutions:**

1. **Regenerate Client**
   ```bash
   poetry run python scripts/regen_client.py
   ```

2. **Check Client Location**
   ```bash
   # Client should be generated in project directory
   ls -la | grep client
   ```

3. **Install Generated Client**
   ```bash
   # If client is generated as separate package
   pip install -e ./generated-client/
   ```

## Installation Issues

### ❌ "Poetry not found" or "pyenv not found"

**Symptoms:**
- Commands not recognized
- Package management failures

**Solutions:**

1. **Install Poetry**
   ```bash
   # Official installer
   curl -sSL https://install.python-poetry.org | python3 -
   
   # Or via pip
   pip install poetry
   ```

2. **Install pyenv (optional but recommended)**
   ```bash
   # macOS with Homebrew
   brew install pyenv
   
   # Linux
   curl https://pyenv.run | bash
   ```

3. **Use System Python**
   ```bash
   # If you can't install pyenv, ensure Python 3.12+
   python3 --version
   python3 -m pip install poetry
   ```

### ❌ "Dependency conflicts"

**Symptoms:**
- Poetry can't resolve dependencies
- Package version conflicts

**Solutions:**

1. **Update Poetry**
   ```bash
   poetry self update
   ```

2. **Clear Cache**
   ```bash
   poetry cache clear pypi --all
   ```

3. **Clean Install**
   ```bash
   rm poetry.lock
   poetry install
   ```

## FAQ

### Q: Can I use API Builder with non-OpenAPI specs?

**A:** Currently, API Builder primarily supports OpenAPI 3.0+ specifications. Support for Postman collections and other formats is planned.

**Workaround:** Convert your API documentation to OpenAPI format using tools like:
- [Postman to OpenAPI Converter](https://github.com/postmanlabs/postman-to-openapi)
- [Insomnia OpenAPI Export](https://docs.insomnia.rest/insomnia/import-export-data)

### Q: How do I handle APIs that require custom authentication?

**A:** API Builder currently supports bearer token authentication. For custom auth:

1. **Modify the client generation**:
   ```bash
   # Edit scripts/regen_client.py to add custom auth headers
   ```

2. **Use environment variables**:
   ```bash
   # Set custom headers in .env file
   CUSTOM_AUTH_HEADER=value
   ```

### Q: Why are some parameters not being auto-resolved?

**A:** API Builder uses parameter name matching to find providers. Common reasons:

1. **Parameter name doesn't match endpoint pattern**
   - `customId` won't match `/merchants` endpoint
   - Add custom mappings in `cli/parameter_detector.py`

2. **Provider endpoint returns unexpected format**
   - Response should be list/array for selection
   - Items should have `id` field or similar

3. **Required parameters missing from dependency chain**
   - Provider endpoint itself needs parameters
   - Creates circular dependency

### Q: How do I handle large API responses?

**A:** API Builder provides several strategies:

1. **Pagination handling**: Automatically fetches all pages
2. **Result limiting**: Shows first 20 items for selection
3. **Data cleaning**: `clean` option removes unnecessary fields
4. **File saving**: Save large results to JSON files

### Q: Can I use API Builder programmatically?

**A:** Yes! The CLI commands wrap the core functionality:

```python
from cli.dependency_analyzer import DependencyAnalyzer
from cli.parameter_detector import ParameterDetector
from cli.utils.api_client import get_client

# Use the same components as the CLI
analyzer = DependencyAnalyzer(openapi_spec)
client = get_client()
```

## Debug Tips

### Enable Debug Logging

```python
# Add to your script
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Generated Client

```bash
# Look at generated client methods
python -c "
from cli.utils.api_client import get_client
client = get_client()
print(dir(client))
"
```

### Check State Files

```bash
# View stored state
ls -la ~/.api-builder/
cat ~/.api-builder/context.json
```

### Validate API Responses

```bash
# Test API directly
curl -H "Authorization: Bearer $TOKEN" \
     $API_BASE_URL/merchants | jq .
```

### Monitor Network Traffic

```bash
# Use mitmproxy to inspect API calls
pip install mitmproxy
mitmdump -s scripts/api_monitor.py
```

## Performance Optimization

### Reduce API Calls

1. **Use cached parameters**: API Builder remembers values within a session
2. **Set defaults**: Pre-populate common date ranges and filters
3. **Batch operations**: Group related API calls when possible

### Optimize Large Datasets

1. **Limit pagination**: Don't fetch all pages if not needed
2. **Use filters**: Apply date ranges and status filters
3. **Clean responses**: Remove unnecessary fields before saving

### Network Optimization

1. **Connection pooling**: Reuse HTTP connections (handled automatically)
2. **Timeout configuration**: Adjust timeouts for slow APIs
3. **Retry logic**: Built-in exponential backoff for failures

## Getting Help

### Community Support

- **GitHub Issues**: [Report bugs and request features](https://github.com/cvanleer/api-builder/issues)
- **GitHub Discussions**: [Ask questions and share tips](https://github.com/cvanleer/api-builder/discussions)

### Debugging Information

When reporting issues, include:

1. **Environment details**:
   ```bash
   python --version
   poetry --version
   poetry show | grep -E "(typer|requests|rich)"
   ```

2. **Error logs**:
   ```bash
   # Enable debug logging
   export API_BUILDER_DEBUG=1
   
   # Run your command and capture output
   poetry run python cli/main.py system query-api > debug.log 2>&1
   ```

3. **API specification**: Sanitized version of your OpenAPI spec
4. **Steps to reproduce**: Exact commands that trigger the issue

### Professional Support

For commercial support, custom integrations, or enterprise deployments, contact the development team through GitHub.

---

## Additional Resources

- [User Guide](USER_GUIDE.md) - Comprehensive usage guide
- [API Reference](api/) - Detailed API documentation
- [Contributing Guide](../CONTRIBUTING.md) - How to contribute to the project
- [Architecture Overview](ARCHITECTURE.md) - System design and components

Happy troubleshooting! 🐛➡️✅