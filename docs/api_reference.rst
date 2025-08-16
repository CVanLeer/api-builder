API Reference
=============

This section contains the complete API reference for API Builder's modules.

CLI Module
----------

Main CLI Interface
~~~~~~~~~~~~~~~~~~

.. automodule:: cli.main
   :members:
   :undoc-members:
   :show-inheritance:

Configuration Management
~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: cli.config
   :members:
   :undoc-members:
   :show-inheritance:

Commands
--------

Authentication Commands
~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: cli.commands.auth
   :members:
   :undoc-members:
   :show-inheritance:

System Commands
~~~~~~~~~~~~~~~

.. automodule:: cli.commands.system
   :members:
   :undoc-members:
   :show-inheritance:

Example Commands
~~~~~~~~~~~~~~~~

.. automodule:: cli.commands.example
   :members:
   :undoc-members:
   :show-inheritance:

Core Components
---------------

Dependency Analyzer
~~~~~~~~~~~~~~~~~~~

.. automodule:: cli.dependency_analyzer
   :members:
   :undoc-members:
   :show-inheritance:

The DependencyAnalyzer class is responsible for:

* Parsing OpenAPI specifications to understand endpoint relationships
* Building dependency graphs between parameters and endpoints
* Determining execution order for complex API workflows
* Detecting circular dependencies and providing fallback strategies

Parameter Detection
~~~~~~~~~~~~~~~~~~~

.. automodule:: cli.parameter_detector
   :members:
   :undoc-members:
   :show-inheritance:

The ParameterDetector provides intelligent parameter type detection:

* **Foreign Keys**: Automatically detects ID parameters (merchantId, locationId, etc.)
* **Dates**: Recognizes date and datetime parameters with smart defaults
* **Enums**: Provides dropdown selections for enumerated values
* **Pagination**: Handles page, limit, and offset parameters
* **Filters**: Detects search and filter parameters

State Management
~~~~~~~~~~~~~~~~

.. automodule:: cli.state
   :members:
   :undoc-members:
   :show-inheritance:

Context Management
~~~~~~~~~~~~~~~~~~

.. automodule:: cli.context
   :members:
   :undoc-members:
   :show-inheritance:

Utilities
---------

API Client
~~~~~~~~~~

.. automodule:: cli.utils.api_client
   :members:
   :undoc-members:
   :show-inheritance:

QAPI Module
-----------

Session Management
~~~~~~~~~~~~~~~~~~

.. automodule:: qapi.retry
   :members:
   :undoc-members:
   :show-inheritance:

Type Definitions
----------------

Parameter Types
~~~~~~~~~~~~~~~

.. autoclass:: cli.parameter_detector.ParameterType
   :members:
   :undoc-members:

.. autoclass:: cli.parameter_detector.ParameterInfo
   :members:
   :undoc-members:

Usage Examples
--------------

Basic SDK Usage
~~~~~~~~~~~~~~~

.. code-block:: python

   from cli.utils.api_client import get_client
   from cli.config import get_saved_token
   
   # Get authenticated client
   client = get_client()
   
   # Make API calls
   merchants = client.merchants.get_merchants.sync()
   print(f"Found {len(merchants['data'])} merchants")

Dependency Analysis
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from cli.dependency_analyzer import DependencyAnalyzer
   import json
   
   # Load OpenAPI spec
   with open('openapi/openai.json') as f:
       spec = json.load(f)
   
   # Analyze dependencies
   analyzer = DependencyAnalyzer(spec)
   providers = analyzer.find_parameter_providers('merchantId')
   print(f"Providers for merchantId: {providers}")

Parameter Detection
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from cli.parameter_detector import ParameterDetector
   
   detector = ParameterDetector()
   param_info = detector.detect_parameter_type('startDate', {
       'type': 'string',
       'format': 'date'
   })
   
   print(f"Parameter type: {param_info.type}")
   # Output: ParameterType.DATE