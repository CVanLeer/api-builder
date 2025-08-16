# API Builder Examples

This directory contains example scripts demonstrating various API Builder features and use cases.

## Quick Start

All examples assume you have:
1. Installed API Builder with `poetry install`
2. Activated the virtual environment with `poetry shell` 
3. Set up authentication with `python cli/main.py auth get-token`
4. Generated your API client with `python scripts/regen_client.py`

## Examples Overview

### Basic Usage
- **`basic_usage.py`** - Simple API connection and data retrieval
- **`authentication.py`** - Different authentication methods

### Data Processing  
- **`postman_import.py`** - Import and use Postman collections (coming soon)
- **`custom_parser.py`** - Create custom response parsers
- **`error_handling.py`** - Robust error handling patterns

### Advanced Workflows
- **`multi_step_workflow.py`** - Complex dependency resolution
- **`batch_processing.py`** - Process multiple API calls efficiently
- **`data_pipeline.py`** - Build ETL pipelines with API data

## Running Examples

```bash
# Navigate to project root
cd /path/to/api-builder

# Run any example script
python examples/basic_usage.py

# Or with full path
poetry run python examples/basic_usage.py
```

## Environment Setup

Create a `.env` file in the project root:

```env
API_BASE_URL=https://api.example.com
API_KEY=your_api_key_here
```

## Need Help?

- Check the [User Guide](../docs/USER_GUIDE.md) for detailed explanations
- See [Troubleshooting](../docs/TROUBLESHOOTING.md) for common issues
- Open an issue on GitHub if you need assistance

## Contributing Examples

We welcome additional examples! Please:
1. Follow the existing code style
2. Include comprehensive docstrings
3. Add error handling
4. Test with real API endpoints
5. Update this README with your example

Happy coding! 🚀