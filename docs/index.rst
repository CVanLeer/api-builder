API Builder Documentation
=========================

Welcome to API Builder's documentation!

API Builder is an intelligent, automated API integration platform that transforms any API documentation into a working Python SDK with CLI interface.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   user_guide
   api_reference
   examples
   troubleshooting
   contributing

Quick Start
-----------

1. **Install API Builder**:

   .. code-block:: bash

      git clone https://github.com/cvanleer/api-builder.git
      cd api-builder
      poetry install
      poetry shell

2. **Set up your API**:

   .. code-block:: bash

      # Place your OpenAPI spec in openapi/openai.json
      poetry run python scripts/regen_client.py

3. **Authenticate**:

   .. code-block:: bash

      poetry run python cli/main.py auth get-token

4. **Start exploring**:

   .. code-block:: bash

      poetry run python cli/main.py system query-api

Features
--------

* **Automatic SDK Generation**: Convert OpenAPI specs to type-safe Python clients
* **Intelligent Parameter Resolution**: Automatically resolve complex parameter dependencies  
* **Interactive CLI**: Rich terminal interface with progress tracking and history
* **Multi-Step Workflows**: Chain multiple API calls seamlessly
* **Error Recovery**: Robust error handling with automatic retry logic
* **Secure Credential Storage**: Encrypted storage of API keys and tokens

Architecture Overview
--------------------

.. code-block:: text

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

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`